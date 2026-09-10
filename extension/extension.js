/**
 * Agtoosa2 VS Code & Cursor IDE Extension
 * Native architecture navigator, blast radius inspector, and drift alarm engine.
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
                new vscode.TreeItem('🎯 User Stories & Requirements (DEV-001 - DEV-013)', vscode.TreeItemCollapsibleState.Collapsed),
                new vscode.TreeItem('🧠 Institutional Architectural Memory Bank', vscode.TreeItemCollapsibleState.Collapsed)
            ];
        }

        const label = element.label || '';
        if (label.includes('Tier 1')) {
            return [
                new vscode.TreeItem('agtoosa/cli/main.py', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/cli/graph_cmd.py', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/cli/lifecycle_cmd.py', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/mcp/server.py', vscode.TreeItemCollapsibleState.None)
            ];
        } else if (label.includes('Tier 2')) {
            return [
                new vscode.TreeItem('agtoosa/graph/store.py (SQLite FTS5)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/graph/metrics.py (Cycle Detection)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/watcher/watcher.py (Continuous Sync)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/review/intelligence.py (Drift Alarms)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/review/ci.py (PR Gate)', vscode.TreeItemCollapsibleState.None)
            ];
        } else if (label.includes('Tier 3')) {
            return [
                new vscode.TreeItem('agtoosa/core/model.py (Domain Entities)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('agtoosa/core/security.py (Zero-Trust Sandbox)', vscode.TreeItemCollapsibleState.None)
            ];
        } else if (label.includes('User Stories')) {
            return [
                new vscode.TreeItem('DEV-011: CI/CD Quality Gate & GitHub Action (✅)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('DEV-012: Standalone Binary Packaging (✅)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('DEV-013: VS Code & Cursor Extension (🔄 Active)', vscode.TreeItemCollapsibleState.None),
                new vscode.TreeItem('DEV-014: Hybrid GraphRAG v2 & Semantic Search (⬜)', vscode.TreeItemCollapsibleState.None)
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

    // 1. Register CodeLens Provider
    const codeLensProvider = new AgtoosaCodeLensProvider(workspaceRoot);
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
    for (const sel of docSelectors) {
        context.subscriptions.push(vscode.languages.registerCodeLensProvider(sel, codeLensProvider));
    }

    // 2. Register Sidebar Views
    const archProvider = new AgtoosaArchitectureTreeProvider(workspaceRoot);
    vscode.window.registerTreeDataProvider('agtoosa.architectureView', archProvider);

    const blastProvider = new AgtoosaBlastRadiusProvider(workspaceRoot);
    vscode.window.registerTreeDataProvider('agtoosa.blastRadiusView', blastProvider);

    const driftProvider = new AgtoosaDriftProvider(workspaceRoot);
    vscode.window.registerTreeDataProvider('agtoosa.driftFindingsView', driftProvider);

    // 3. Register Status Bar
    const statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
    statusBar.text = '$(shield) Agtoosa: Ready';
    statusBar.tooltip = 'Click to open Agtoosa Architecture Command Center';
    statusBar.command = 'agtoosa.openVisualizer';
    statusBar.show();
    context.subscriptions.push(statusBar);

    // 4. Register Commands
    context.subscriptions.push(vscode.commands.registerCommand('agtoosa.rebuildGraph', async () => {
        vscode.window.showInformationMessage('Agtoosa: Rebuilding knowledge graph...');
        try {
            await runAgtoosaCli(['graph', 'build'], workspaceRoot);
            vscode.window.showInformationMessage('✅ Agtoosa: Knowledge graph rebuilt successfully!');
            archProvider.refresh();
            codeLensProvider.refresh();
            driftProvider.review();
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

    // Auto-refresh CodeLens on document save
    context.subscriptions.push(vscode.workspace.onDidSaveTextDocument(() => {
        codeLensProvider.refresh();
    }));

    // Initial drift review on activate
    driftProvider.review();
}

function deactivate() {}

module.exports = {
    activate,
    deactivate
};
