"""Terminal output formatting with ANSI colors."""

import sys

# ANSI codes
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
RESET = "\033[0m"

PREVIEW_LENGTH = 500


def _supports_color() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    if _supports_color():
        return f"{code}{text}{RESET}"
    return text


def print_header(text: str) -> None:
    width = 60
    print()
    print(_c(CYAN + BOLD, "=" * width))
    print(_c(CYAN + BOLD, f"  {text}"))
    print(_c(CYAN + BOLD, "=" * width))


def print_subheader(text: str) -> None:
    print()
    print(_c(YELLOW + BOLD, f"── {text} ──"))


def print_prompt(prompt: str) -> None:
    print_subheader("Prompt")
    print(_c(DIM, prompt.strip()))


def print_round1(responses: list[dict]) -> None:
    """Print Round 1 response previews.

    Each response dict: {model_name, response, latency, error}
    """
    print_header("ROUND 1 — Responses")

    for r in responses:
        name = r["model_name"]
        if r["error"]:
            err = r["error"]
            print(f"\n  {_c(BOLD, name)}: {_c(RED, f'ERROR — {err}')}")
        else:
            latency = r["latency"]
            text = r["response"].strip()
            preview = text[:PREVIEW_LENGTH]
            if len(text) > PREVIEW_LENGTH:
                preview += "..."
            print(f"\n  {_c(BOLD, name)} {_c(DIM, f'({latency:.1f}s)')}")
            for line in preview.split("\n"):
                print(f"    {line}")


def print_round2(judgments: list[dict]) -> None:
    """Print Round 2 judge results.

    Each judgment dict: {judge_name, winner, rankings, reasoning, degraded}
    """
    print_header("ROUND 2 — Judgments")

    for j in judgments:
        judge = j["judge_name"]
        winner = j["winner"]
        reasoning = j["reasoning"]
        rankings = j.get("rankings", [])
        degraded = j.get("degraded", False)

        label = _c(BOLD, judge)
        if degraded:
            label += _c(RED, " [degraded]")

        print(f"\n  {label}")
        print(f"    Winner: {_c(GREEN + BOLD, winner)}")
        if rankings:
            ranking_str = " > ".join(rankings)
            print(f"    Ranking: {_c(DIM, ranking_str)}")
        print(f"    Reasoning: {_c(DIM, reasoning)}")


def print_round3(final: dict) -> None:
    """Print Round 3 final tally.

    final dict: {winner, points, votes, breakdown}
    """
    print_header("ROUND 3 — Final Results")

    points = final["points"]
    votes = final["votes"]
    winner = final["winner"]

    # Sort by points descending
    sorted_models = sorted(points.items(), key=lambda x: x[1], reverse=True)

    if not sorted_models:
        print(f"\n  {_c(RED, 'No results to tally.')}")
        return

    max_pts = max(p for _, p in sorted_models) if sorted_models else 1

    print()
    for name, pts in sorted_models:
        vote_count = votes.get(name, 0)
        bar_len = int((pts / max(max_pts, 1)) * 30)
        bar = "█" * bar_len
        is_winner = name == winner
        name_str = _c(GREEN + BOLD, name) if is_winner else name
        pts_str = f"{pts} pts, {vote_count} vote{'s' if vote_count != 1 else ''}"
        marker = _c(GREEN + BOLD, " ★ WINNER") if is_winner else ""
        print(f"  {name_str:<20s} {_c(CYAN, bar)} {pts_str}{marker}")

    print()
    print(
        _c(BOLD, f"  Overall Winner: ")
        + _c(GREEN + BOLD, winner if winner else "Tie / No clear winner")
    )
    print()


def print_skip_eval_message() -> None:
    print()
    print(_c(YELLOW, "  Evaluation skipped (--no-eval flag or fewer than 2 responses)."))
    print()


def print_error(msg: str) -> None:
    print(_c(RED + BOLD, f"\n  Error: {msg}\n"))
