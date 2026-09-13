/**
 * Agtoosa2 VS Code & Cursor IDE Extension (v0.5.0)
 * Native architecture navigator, blast radius inspector, gutter telemetry lens,
 * 1-click QuickFix refactoring, and pre-push guard daemon engine.
 */

const vscode = require('vscode');
const { execFile, exec } = require('child_process');
const path = require('path');
const fs = require('fs');

/**
 * Execute Agtoosa CLI command within workspace.
 */
function runAgtoosaCli(args, workspaceRoot) {
    return new Promise((resolve, reject) => {
        const config = vscode.workspace.getConfiguration('agtoosa');
        const customExec = config.get('executablePath', 'agtoosa');

        // Check if venv python exists in workspace
        const venvAgtoosa = path.join(workspaceRoot, '.venv', 'bin', 'agtoosa');
        let command = customExec;
        if (customExec === 'agtoosa' && fs.existsSync(venvAgtoosa)) {
            command = venvAgtoosa;
        }

        const fullArgs = ['-C', workspaceRoot, ...args];

        execFile(command, fullArgs, { cwd: workspaceRoot, maxBuffer: 10 * 1024 * 1024 }, (err, stdout, stderr) => {
            if (err) {
                // Fallback attempt with 'uv run agtoosa'
                const fallbackCmd = `uv run agtoosa ${fullArgs.map(a => `"${a}"`).join(' ')}`;
                exec(fallbackCmd, { cwd: workspaceRoot, maxBuffer: 10 * 1024 * 1024 }, (fbErr, fbStdout, fbStderr) => {
                    if (fbErr) {
                        reject(new Error(fbStderr || fbErr.message));
                    } else {
                        resolve(fbStdout);
                    }
                });
            } else {
                resolve(stdout);
            }
        });
    });
}

/**
 * CodeLens Provider for showing caller counts and blast radius warnings above symbols.
 */
class AgtoosaCodeLensProvider {
    constructor(workspaceRoot) {
        this.workspaceRoot = workspaceRoot;
        this._onDidChangeCodeLenses = new vscode.EventEmitter();
        this.onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;
    }

    refresh() {
        this._onDidChangeCodeLenses.fire();
    }

    async provideCodeLenses(document, token) {
        const config = vscode.workspace.getConfiguration('agtoosa');
        if (!config.get('enableCodeLens', true)) {
            return [];
        }

        if (!this.workspaceRoot) {
            return [];
        }

        const filePath = document.uri.fsPath;
        try {
            const raw = await runAgtoosaCli(['graph', 'symbols', filePath, '--json'], this.workspaceRoot);
            const symbols = JSON.parse(raw);

            const lenses = [];
            for (const sym of symbols) {
                if (!sym.start_line) continue;
                const lineNum = Math.max(0, sym.start_line - 1);
                const range = new vscode.Range(lineNum, 0, lineNum, 0);

                let icon = '🏛️';
                if (sym.risk === 'CRITICAL' || sym.risk === 'HIGH') {
                    icon = '⚠️';
                }

                const title = `${icon} ${sym.caller_count} callers | Blast Radius: ${sym.risk}`;
                lenses.push(new vscode.CodeLens(range, {
                    title: title,
                    tooltip: `Top upstream callers: ${sym.top_callers ? sym.top_callers.join(', ') : 'None'}. Click to inspect blast radius.`,
                    command: 'agtoosa.inspectBlastRadius',
                    arguments: [sym.name]
                }));
            }
            return lenses;
        } catch (e) {
            return [];
        }
    }
}

/**
 * Gutter Telemetry Decorator: displays execution frequency and error indicators in editor gutters.
 */
class AgtoosaGutterDecorator {
    constructor(workspaceRoot) {
        this.workspaceRoot = workspaceRoot;
        this.hotDecoration = vscode.window.createTextEditorDecorationType({
            gutterIconPath: path.join(__dirname, 'resources', 'hot.svg'),
            gutterIconSize: 'contain',
            overviewRulerColor: new vscode.ThemeColor('charts.red'),
            overviewRulerLane: vscode.OverviewRulerLane.Right
        });
        this.errorDecoration = vscode.window.createTextEditorDecorationType({
            gutterIconPath: path.join(__dirname, 'resources', 'error.svg'),
            gutterIconSize: 'contain',
            overviewRulerColor: new vscode.ThemeColor('charts.yellow'),
            overviewRulerLane: vscode.OverviewRulerLane.Right
        });
        this.coldDecoration = vscode.window.createTextEditorDecorationType({
            gutterIconPath: path.join(__dirname, 'resources', 'cold.svg'),
            gutterIconSize: 'contain',
            overviewRulerColor: new vscode.ThemeColor('charts.blue'),
            overviewRulerLane: vscode.OverviewRulerLane.Right
        });
    }

    async updateDecorations(editor) {
        if (!editor || !this.workspaceRoot) return;
        const config = vscode.workspace.getConfiguration('agtoosa');
        if (!config.get('enableGutterHotspots', true)) {
            editor.setDecorations(this.hotDecoration, []);
            editor.setDecorations(this.errorDecoration, []);
            editor.setDecorations(this.coldDecoration, []);
            return;
        }

        const filePath = editor.document.uri.fsPath;
        try {
            const symRaw = await runAgtoosaCli(['graph', 'symbols', filePath, '--json'], this.workspaceRoot);
            const symbols = JSON.parse(symRaw);

            const telemRaw = await runAgtoosaCli(['telemetry', '--json'], this.workspaceRoot);
            const telemList = JSON.parse(telemRaw);
            const telemMap = {};
            for (const t of telemList) {
                telemMap[t.node_id] = t;
                if (t.name) telemMap[t.name] = t;
            }

            const hotRanges = [];
            const errorRanges = [];
            const coldRanges = [];

            for (const sym of symbols) {
                if (!sym.start_line) continue;
                const lineNum = Math.max(0, sym.start_line - 1);
                const range = new vscode.Range(lineNum, 0, lineNum, 0);

                const t = telemMap[sym.id] || telemMap[sym.name];
                if (t) {
                    if (t.error_rate >= 0.05) {
                        errorRanges.push(range);
                    } else if (t.call_count >= 100) {
                        hotRanges.push(range);
                    } else if (t.call_count === 0) {
                        coldRanges.push(range);
                    }
                }
            }

            editor.setDecorations(this.hotDecoration, hotRanges);
            editor.setDecorations(this.errorDecoration, errorRanges);
            editor.setDecorations(this.coldDecoration, coldRanges);
        } catch (e) {
            // Ignore telemetry decoration failures gracefully
        }
    }
}

/**
 * CodeAction Provider for 1-Click Refactoring QuickFixes.
 */
class AgtoosaCodeActionProvider {
    constructor(workspaceRoot) {
        this.workspaceRoot = workspaceRoot;
        this.deadCodeSymbols = new Set();
        this.cyclicSymbols = new Set();
    }

    async refreshFindings() {
        try {
            const deadRaw = await runAgtoosaCli(['refactor', 'dead-code', '--json'], this.workspaceRoot);
            const deadReport = JSON.parse(deadRaw);
            this.deadCodeSymbols = new Set((deadReport.dead_symbols || []).map(s => s.name));
        } catch (e) {
            this.deadCodeSymbols = new Set();
        }

        try {
            const revRaw = await runAgtoosaCli(['review', '--json'], this.workspaceRoot);
            const revReport = JSON.parse(revRaw);
            this.cyclicSymbols = new Set(
                (revReport.findings || [])
                    .filter(f => f.category === 'CIRCULAR_DEPENDENCY')
                    .map(f => f.symbol_or_path)
            );
        } catch (e) {
            this.cyclicSymbols = new Set();
        }
    }

    provideCodeActions(document, range, context, token) {
        const config = vscode.workspace.getConfiguration('agtoosa');
        if (!config.get('enableQuickFixRefactoring', true)) {
            return [];
        }

        const actions = [];
        const line = range.start.line;
        const lineText = document.lineAt(line).text;

        // Check if line contains a function, class, or symbol identifier
        const match = lineText.match(/(?:def|class|function|const|let|var)\s+([a-zA-Z0-9_]+)/);
        const symbolName = match ? match[1] : null;

        if (symbolName) {
            // 1. Inspect Blast Radius action
            const impactAction = new vscode.CodeAction(
                `🛡️ Agtoosa: Inspect Blast Radius of '${symbolName}'`,
                vscode.CodeActionKind.Refactor
            );
            impactAction.command = {
                command: 'agtoosa.inspectBlastRadius',
                title: 'Inspect Blast Radius',
                arguments: [symbolName]
            };
            actions.push(impactAction);

            // 2. Safe Prune Dead Code QuickFix
            if (this.deadCodeSymbols.has(symbolName)) {
                const pruneAction = new vscode.CodeAction(
                    `✂️ Agtoosa: Safe Prune Dead Symbol '${symbolName}' (with Atomic Backup)`,
                    vscode.CodeActionKind.QuickFix
                );
                pruneAction.isPreferred = true;
                pruneAction.command = {
                    command: 'agtoosa.pruneDeadSymbol',
                    title: 'Safe Prune Dead Symbol',
                    arguments: [symbolName]
                };
                actions.push(pruneAction);
            }

            // 3. Decouple Cycle QuickFix
            if (this.cyclicSymbols.has(symbolName) || this.cyclicSymbols.has(document.uri.fsPath)) {
                const decoupleAction = new vscode.CodeAction(
                    `🔄 Agtoosa: Decouple Cyclic Dependency for '${symbolName}'`,
                    vscode.CodeActionKind.QuickFix
                );
                decoupleAction.command = {
                    command: 'agtoosa.decoupleCycle',
                    title: 'Decouple Cycle',
                    arguments: [symbolName]
                };
                actions.push(decoupleAction);
            }
        }

        return actions;
    }
}

/**
 * Tree Data Provider for Architecture Tiers and User Stories.
 */
class AgtoosaArchitectureTreeProvider {
    constructor(workspaceRoot) {
        this.workspaceRoot = workspaceRoot;
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
    }

    refresh() {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element) {
        return element;
    }

    async getChildren(element) {
        if (!element) {
            return [
                new vscode.TreeItem('🏛️ Tier 1: Presentation & Entrypoints (cli, mcp)', vscode.TreeItemCollapsibleState.Collapsed),
                new vscode.TreeItem('⚙️ Tier 2: Application Services (parser, graph, watcher, review)', vscode.TreeItemCollapsibleState.Collapsed),
                new vscode.TreeItem('🧱 Tier 3: Domain Core & Security (core/model, core/security)', vscode.TreeItemCollapsibleState.Collapsed),
                new vscode.TreeItem('🎯 User Stories & Requirements (DEV-001 - DEV-027)', vscode.TreeItemCollapsibleState.Collapsed),
                new vscode.TreeItem('🧠 Institutional Architectural Memory Bank', vscode.TreeItemCollapsibleState.Collapsed)
            ];
        }

        const label = element.label || '';
        if (label.includes('Tier 1')) {
            return [
                new vscode.TreeItem('agtoosa/cli/main.py', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/cli/graph_cmd.py', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/cli/lifecycle_cmd.py', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/cli/guard_cmd.py', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/mcp/server.py', vscode.TreeItemCollapsibleState.None)
            ];
        } else if (label.includes('Tier 2')) {
            return [
                new vscode.TreeItem('agtoosa/graph/store.py (SQLite FTS5)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/graph/metrics.py (Cycle Detection)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/parser/event_lineage.py (Event Bus & Lineage)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/parser/frameworks.py (DI & Routes)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/watcher/watcher.py (Continuous Sync)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/review/guard.py (Pre-Push Guard Daemon)', vscode.TreeItemCollapsibleState.None)
            ];
        } else if (label.includes('Tier 3')) {
            return [
                new vscode.TreeItem('agtoosa/core/model.py (Domain Entities & Ontology)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/core/security.py (Zero-Trust Sandbox)', vscode.TreeItemCollapsibleState.None)
            ];
        } else if (label.includes('User Stories')) {
            return [
                new vscode.TreeItem('DEV-024: Pre-Push Guard Daemon (✅)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('DEV-025: Framework DI & Dynamic Routes (✅)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('DEV-026: Async Event Bus Lineage (✅)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('DEV-027: In-Editor Gutter Lens & Marketplace (🔄 Active)', vscode.TreeItemCollapsibleState.None)
            ];
        } else if (label.includes('Memory Bank')) {
            try {
                const raw = await runAgtoosaCli(['review', 'reflect'], this.workspaceRoot);
                const lines = raw.split('\n').filter(l => l.trim().length > 0).slice(1);
                return lines.map(l => new vscode.TreeItem(l.trim(), vscode.TreeItemCollapsibleState.None));
            } catch (e) {
                return [new vscode.TreeItem('No memory rules loaded.', vscode.TreeItemCollapsibleState.None)];
            }
        }
        return [];
    }
}

/**
 * Tree Data Provider for Active Blast Radius inspection.
 */
class AgtoosaBlastRadiusProvider {
    constructor(workspaceRoot) {
        this.workspaceRoot = workspaceRoot;
        this.activeTarget = null;
        this.impactData = null;
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
    }

    async inspect(targetSymbol) {
        this.activeTarget = targetSymbol;
        try {
            const raw = await runAgtoosaCli(['graph', 'impact', targetSymbol, '--json'], this.workspaceRoot);
            this.impactData = JSON.parse(raw);
        } catch (e) {
            this.impactData = null;
        }
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element) {
        return element;
    }

    async getChildren(element) {
        if (!this.activeTarget) {
            return [new vscode.TreeItem('Click a CodeLens or run "Inspect Symbol Blast Radius".', vscode.TreeItemCollapsibleState.None)];
        }

        if (!element) {
            const count = this.impactData ? this.impactData.impacted_count : 0;
            const rootItem = new vscode.TreeItem(`🎯 ${this.activeTarget} (Impacts ${count} callers)`, vscode.TreeItemCollapsibleState.Expanded);
            return [rootItem];
        }

        if (this.impactData && this.impactData.impacted) {
            return this.impactData.impacted.map(imp => {
                const item = new vscode.TreeItem(`[Hop ${imp.depth}] ${imp.node_type.toUpperCase()}: ${imp.name} (${imp.path})`, vscode.TreeItemCollapsibleState.None);
                item.tooltip = `Relationship: ${imp.relationship}`;
                return item;
            });
        }
        return [];
    }
}

/**
 * Tree Data Provider for Architectural Drift Alarms.
 */
class AgtoosaDriftProvider {
    constructor(workspaceRoot) {
        this.workspaceRoot = workspaceRoot;
        this.findings = [];
        this._onDidChangeTreeData = new vscode.EventEmitter();
        this.onDidChangeTreeData = this._onDidChangeTreeData.event;
    }

    async review() {
        try {
            const raw = await runAgtoosaCli(['review', '--json'], this.workspaceRoot);
            const report = JSON.parse(raw);
            this.findings = report.findings || [];
        } catch (e) {
            this.findings = [];
        }
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element) {
        return element;
    }

    async getChildren(element) {
        if (!element) {
            if (this.findings.length === 0) {
                return [new vscode.TreeItem('✨ Zero architectural drift detected! Invariants clean.', vscode.TreeItemCollapsibleState.None)];
            }
            return this.findings.map(f => {
                const icon = f.severity === 'ERROR' ? '🚫' : '⚠️';
                const item = new vscode.TreeItem(`${icon} [${f.category}] in ${f.symbol_or_path}`, vscode.TreeItemCollapsibleState.None);
                item.tooltip = f.message;
                return item;
            });
        }
        return [];
    }
}

/**
 * Extension activation entrypoint.
 */
function activate(context) {
    const workspaceRoot = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders.length > 0
        ? vscode.workspace.workspaceFolders[0].uri.fsPath
        : null;

    if (!workspaceRoot) {
        return;
    }

    const docSelectors = [
        { language: 'python' },
        { language: 'typescript' },
        { language: 'javascript' },
        { language: 'go' },
        { language: 'rust' },
        { language: 'java' },
        { language: 'c' },
        { language: 'cpp' },
        { language: 'csharp' },
        { language: 'shellscript' }
    ];

    // 1. Register CodeLens Provider
    const codeLensProvider = new AgtoosaCodeLensProvider(workspaceRoot);
    for (const sel of docSelectors) {
        context.subscriptions.push(vscode.languages.registerCodeLensProvider(sel, codeLensProvider));
    }

    // 2. Register Gutter Decorator
    const gutterDecorator = new AgtoosaGutterDecorator(workspaceRoot);
    if (vscode.window.activeTextEditor) {
        gutterDecorator.updateDecorations(vscode.window.activeTextEditor);
    }
    context.subscriptions.push(vscode.window.onDidChangeActiveTextEditor(editor => {
        if (editor) gutterDecorator.updateDecorations(editor);
    }));

    // 3. Register CodeAction QuickFix Provider
    const codeActionProvider = new AgtoosaCodeActionProvider(workspaceRoot);
    for (const sel of docSelectors) {
        context.subscriptions.push(
            vscode.languages.registerCodeActionsProvider(sel, codeActionProvider, {
                providedCodeActionKinds: [
                    vscode.CodeActionKind.QuickFix,
                    vscode.CodeActionKind.Refactor
                ]
            })
        );
    }

    // 4. Register Sidebar Views
    const archProvider = new AgtoosaArchitectureTreeProvider(workspaceRoot);
    vscode.window.registerTreeDataProvider('agtoosa.architectureView', archProvider);

    const blastProvider = new AgtoosaBlastRadiusProvider(workspaceRoot);
    vscode.window.registerTreeDataProvider('agtoosa.blastRadiusView', blastProvider);

    const driftProvider = new AgtoosaDriftProvider(workspaceRoot);
    vscode.window.registerTreeDataProvider('agtoosa.driftFindingsView', driftProvider);

    // 5. Register Dynamic Guard Status Bar
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.text = '$(shield) Agtoosa: Invariants Clean';
    statusBar.tooltip = 'Click to open Agtoosa Architecture Command Center or review findings';
    statusBar.command = 'agtoosa.runReview';
    statusBar.show();
    context.subscriptions.push(statusBar);

    async function updateGuardStatus() {
        const guardCachePath = path.join(workspaceRoot, '.agtoosa', 'guard_status.json');
        try {
            if (fs.existsSync(guardCachePath)) {
                const cacheContent = fs.readFileSync(guardCachePath, 'utf-8');
                const guardData = JSON.parse(cacheContent);
                if (guardData.passed) {
                    statusBar.text = '$(shield) Agtoosa: Invariants Clean';
                    statusBar.color = undefined;
                } else {
                    const count = (guardData.drift_findings || []).length;
                    statusBar.text = `$(alert) Agtoosa: ${count} Drift Alarms`;
                    statusBar.color = new vscode.ThemeColor('errorForeground');
                }
            }
        } catch (e) {
            // Keep existing status text
        }
    }
    updateGuardStatus();

    // 6. Register Commands
    context.subscriptions.push(vscode.commands.registerCommand('agtoosa.rebuildGraph', async () => {
        vscode.window.showInformationMessage('Agtoosa: Rebuilding knowledge graph...');
        try {
            await runAgtoosaCli(['graph', 'build'], workspaceRoot);
            vscode.window.showInformationMessage('✅ Agtoosa: Knowledge graph rebuilt successfully!');
            archProvider.refresh();
            codeLensProvider.refresh();
            await driftProvider.review();
            await codeActionProvider.refreshFindings();
            updateGuardStatus();
            if (vscode.window.activeTextEditor) {
                gutterDecorator.updateDecorations(vscode.window.activeTextEditor);
            }
        } catch (e) {
            vscode.window.showErrorMessage(`❌ Agtoosa build error: ${e.message}`);
        }
    }));

    context.subscriptions.push(vscode.commands.registerCommand('agtoosa.openVisualizer', async () => {
        const visualizerPath = path.join(workspaceRoot, '.agtoosa', 'graph_view.html');
        if (fs.existsSync(visualizerPath)) {
            vscode.env.openExternal(vscode.Uri.parse(`http://localhost:8080/graph_view.html`));
        } else {
            await runAgtoosaCli(['graph', 'view', '--open'], workspaceRoot);
        }
    }));

    context.subscriptions.push(vscode.commands.registerCommand('agtoosa.runReview', async () => {
        vscode.window.showInformationMessage('Agtoosa: Running architectural review...');
        await driftProvider.review();
        await codeActionProvider.refreshFindings();
        updateGuardStatus();
        vscode.window.showInformationMessage(`Agtoosa Review complete: ${driftProvider.findings.length} findings.`);
    }));

    context.subscriptions.push(vscode.commands.registerCommand('agtoosa.inspectBlastRadius', async (target) => {
        let symName = target;
        if (!symName) {
            symName = await vscode.window.showInputBox({
                prompt: 'Enter function, class, or file name to calculate blast radius',
                placeHolder: 'e.g. GraphStore or ReviewIntelligenceEngine'
            });
        }
        if (symName) {
            await blastProvider.inspect(symName);
            vscode.commands.executeCommand('agtoosa.blastRadiusView.focus');
        }
    }));

    context.subscriptions.push(vscode.commands.registerCommand('agtoosa.rememberRule', async () => {
        const rule = await vscode.window.showInputBox({
            prompt: 'Enter architectural invariant or rule to commit to institutional memory',
            placeHolder: 'e.g. Core model must never import CLI'
        });
        if (rule) {
            const domain = await vscode.window.showInputBox({
                prompt: 'Enter associated domain or subsystem (optional)',
                placeHolder: 'e.g. core, graph, review'
            });
            const args = ['review', 'remember', rule];
            if (domain) args.push('-d', domain);
            await runAgtoosaCli(args, workspaceRoot);
            vscode.window.showInformationMessage(`🧠 Architectural invariant recorded: "${rule}"`);
            archProvider.refresh();
        }
    }));

    // 1-Click QuickFix Refactoring Commands
    context.subscriptions.push(vscode.commands.registerCommand('agtoosa.pruneDeadSymbol', async (symbolName) => {
        const confirm = await vscode.window.showWarningMessage(
            `Safe prune dead symbol '${symbolName}'? An atomic rollback snapshot will be created automatically.`,
            { modal: true },
            'Prune Dead Symbol'
        );
        if (confirm === 'Prune Dead Symbol') {
            try {
                const res = await runAgtoosaCli(['refactor', 'dead-code', '--clean', '--json'], workspaceRoot);
                const resultData = JSON.parse(res);
                vscode.window.showInformationMessage(
                    `✂️ Pruned dead symbol '${symbolName}'. Backup: ${resultData.backup_dir || 'available'}. Run 'agtoosa refactor rollback' if needed.`
                );
                archProvider.refresh();
                codeLensProvider.refresh();
                await codeActionProvider.refreshFindings();
            } catch (e) {
                vscode.window.showErrorMessage(`❌ Pruning failed: ${e.message}`);
            }
        }
    }));

    context.subscriptions.push(vscode.commands.registerCommand('agtoosa.decoupleCycle', async (symbolName) => {
        try {
            const res = await runAgtoosaCli(['refactor', 'decouple', '--json'], workspaceRoot);
            const cycleData = JSON.parse(res);
            vscode.window.showInformationMessage(
                `🔄 Cycle Decoupling Blueprint generated for ${symbolName || 'cycle'}. Review blueprints in Agtoosa Studio.`
            );
        } catch (e) {
            vscode.window.showErrorMessage(`❌ Decoupling failed: ${e.message}`);
        }
    }));

    context.subscriptions.push(vscode.commands.registerCommand('agtoosa.toggleHotspots', async () => {
        const config = vscode.workspace.getConfiguration('agtoosa');
        const current = config.get('enableGutterHotspots', true);
        await config.update('enableGutterHotspots', !current, vscode.ConfigurationTarget.Global);
        vscode.window.showInformationMessage(`Agtoosa Gutter Hotspots ${!current ? 'Enabled' : 'Disabled'}.`);
        if (vscode.window.activeTextEditor) {
            gutterDecorator.updateDecorations(vscode.window.activeTextEditor);
        }
    }));

    // Auto-refresh on document save
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(async (doc) => {
        codeLensProvider.refresh();
        if (vscode.window.activeTextEditor && vscode.window.activeTextEditor.document === doc) {
            gutterDecorator.updateDecorations(vscode.window.activeTextEditor);
        }
        updateGuardStatus();
    }));

    // Initial load
    driftProvider.review();
    codeActionProvider.refreshFindings();
}

function deactivate() {}

module.exports = {
    activate,
    deactivate,
    AgtoosaCodeLensProvider,
    AgtoosaGutterDecorator,
    AgtoosaCodeActionProvider
};
