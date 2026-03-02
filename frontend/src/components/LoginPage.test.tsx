import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginPage } from "@/components/LoginPage";
import * as AuthContext from "@/components/AuthContext";
import { vi } from "vitest";

const mockAuth = {
    token: null,
    username: null,
    isLoading: false,
    error: null,
    login: vi.fn(),
    logout: vi.fn(),
};

describe("LoginPage", () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.spyOn(AuthContext, "useAuth").mockReturnValue({ ...mockAuth });
    });

    it("renders the login form", () => {
        render(<LoginPage />);
        expect(screen.getByText("Sign in to Kanban Studio")).toBeInTheDocument();
        expect(screen.getByLabelText(/username/i)).toBeInTheDocument();
        expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: /sign in/i })).toBeInTheDocument();
    });

    it("calls login with entered credentials", async () => {
        mockAuth.login.mockResolvedValue(true);
        vi.spyOn(AuthContext, "useAuth").mockReturnValue({ ...mockAuth });

        render(<LoginPage />);
        await userEvent.type(screen.getByLabelText(/username/i), "user");
        await userEvent.type(screen.getByLabelText(/password/i), "password");
        await userEvent.click(screen.getByRole("button", { name: /sign in/i }));

        expect(mockAuth.login).toHaveBeenCalledWith("user", "password");
    });

    it("displays an error message", () => {
        vi.spyOn(AuthContext, "useAuth").mockReturnValue({
            ...mockAuth,
            error: "Invalid username or password",
        });

        render(<LoginPage />);
        expect(screen.getByRole("alert")).toHaveTextContent("Invalid username or password");
    });
});
