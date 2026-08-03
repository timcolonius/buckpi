"""Safe, small LaTeX-style formatter for physical-variable labels."""

from __future__ import annotations

from html import escape


class SymbolError(ValueError):
    """Raised when a variable label contains unsupported symbol markup."""


COMMANDS = {
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ",
    "epsilon": "ε", "varepsilon": "ϵ", "zeta": "ζ", "eta": "η",
    "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ",
    "lambda": "λ", "mu": "μ", "nu": "ν", "xi": "ξ", "omicron": "ο",
    "pi": "π", "varpi": "ϖ", "rho": "ρ", "varrho": "ϱ", "sigma": "σ",
    "varsigma": "ς", "tau": "τ", "upsilon": "υ", "phi": "φ",
    "varphi": "ϕ", "chi": "χ", "psi": "ψ", "omega": "ω",
    "Gamma": "Γ", "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ",
    "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ", "Psi": "Ψ",
    "Omega": "Ω", "infty": "∞", "partial": "∂", "nabla": "∇", "ell": "ℓ",
}

UNICODE_TO_LATEX = {value: f"\\{name}" for name, value in COMMANDS.items()}


class _Parser:
    def __init__(self, text: str):
        self.text = text
        self.position = 0

    def parse(self, closing: str | None = None) -> str:
        output = []
        while self.position < len(self.text):
            character = self.text[self.position]
            if closing and character == closing:
                self.position += 1
                return "".join(output)
            if character == "}":
                raise SymbolError("Unmatched '}' in variable label")
            if character == "\\":
                output.append(self.command())
            elif character in "_^":
                self.position += 1
                tag = "sub" if character == "_" else "sup"
                output.append(f"<{tag}>{self.atom()}</{tag}>")
            elif character == "{":
                self.position += 1
                output.append(self.parse("}"))
            else:
                output.append(escape(character))
                self.position += 1
        if closing:
            raise SymbolError("Unclosed '{' in variable label")
        return "".join(output)

    def command(self) -> str:
        self.position += 1
        start = self.position
        while self.position < len(self.text) and self.text[self.position].isalpha():
            self.position += 1
        command = self.text[start:self.position]
        if not command:
            raise SymbolError("A backslash must be followed by a symbol name")
        try:
            return COMMANDS[command]
        except KeyError as exc:
            raise SymbolError(f"Unsupported symbol command '\\{command}'") from exc

    def atom(self) -> str:
        if self.position >= len(self.text):
            raise SymbolError("A subscript or superscript needs a value")
        if self.text[self.position] == "{":
            self.position += 1
            return self.parse("}")
        if self.text[self.position] == "\\":
            return self.command()
        character = self.text[self.position]
        self.position += 1
        return escape(character)


def symbol_html(label: str) -> str:
    """Render a controlled LaTeX-style variable label as safe HTML."""
    return _Parser(label.strip()).parse()


def symbol_latex(label: str) -> str:
    """Return validated LaTeX source suitable for rendering with KaTeX."""
    cleaned = label.strip()
    _Parser(cleaned).parse()  # Validate commands and balanced groups.
    output = []
    for character in cleaned:
        if character in UNICODE_TO_LATEX:
            output.append(UNICODE_TO_LATEX[character] + " ")
        elif character in "$%&#~":
            output.append("\\" + character)
        elif character == "<":
            output.append("\\lt ")
        elif character == ">":
            output.append("\\gt ")
        else:
            output.append(character)
    return "".join(output)
