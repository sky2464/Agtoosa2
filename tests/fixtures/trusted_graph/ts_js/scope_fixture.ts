// WHY: Test fixture for TS scoped symbols, arrow callbacks, and export aliases (DEV-041/046)

export class AuthService {
    // NOTE: Authenticate user
    authenticate(token: string): boolean {
        return token.length > 0;
    }
}

export class PaymentGateway {
    // Same method name in different class
    authenticate(apiKey: string): boolean {
        return apiKey.startsWith("sk_");
    }
}

// Nested callback containing inner function
export function processBatch(items: string[]): void {
    items.forEach((item) => {
        const transform = (x: string) => x.trim();
        transform(item);
    });
}

// String and comment that resemble real code
const codeTemplate = "function fakeInner() { return true; }";
// function commentedOutFunction() { return false; }
