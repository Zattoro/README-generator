"""Markdown formatting helpers."""

from __future__ import annotations


def badge(label: str, message: str, color: str = "blue") -> str:
    """Return a shields.io markdown badge."""
    return f"![{label}](https://img.shields.io/badge/{label}-{message}-{color})"


def tech_badges(tech_stack: list[str]) -> str:
    """Generate a row of tech-stack badges."""
    color_map = {
        "Python": "blue",
        "JavaScript": "yellow",
        "TypeScript": "blue",
        "Go": "cyan",
        "Rust": "orange",
        "Java": "red",
        "PHP": "purple",
        "Ruby": "red",
        "C++": "blue",
        "Docker": "blue",
    }
    badges = []
    for tech in tech_stack:
        color = color_map.get(tech, "gray")
        badges.append(badge("stack", tech.replace(" ", "%20"), color))
    return " ".join(badges)