#!/usr/bin/env python3
import argparse
import sys
from agent import CompanyAgent
from generator import EmployeeGenerator
from presets import get_preset, INDUSTRY_CHOICES


def main():
    parser = argparse.ArgumentParser(
        description="Generate fake employees for identity management"
    )
    parser.add_argument("company", nargs="?", help="Company name (required for LLM providers)")
    parser.add_argument(
        "-n",
        "--num",
        type=int,
        default=100,
        help="Number of employees to generate (default: 100)",
    )
    parser.add_argument(
        "-f",
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)",
    )
    parser.add_argument(
        "-p",
        "--provider",
        choices=["ollama", "apfel", "none"],
        default="ollama",
        help="LLM provider: ollama (default), apfel (Apple Intelligence), or none (use built-in preset)",
    )
    parser.add_argument(
        "-i",
        "--industry",
        choices=INDUSTRY_CHOICES,
        metavar="INDUSTRY",
        help=(
            f"Industry preset for --provider none. "
            f"Choices: {', '.join(INDUSTRY_CHOICES)}"
        ),
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file (default: stdout)",
    )
    args = parser.parse_args()

    # Validate argument combinations
    if args.provider == "none":
        if not args.industry:
            parser.error(
                f"--industry is required when --provider none. "
                f"Choices: {', '.join(INDUSTRY_CHOICES)}"
            )
    else:
        if not args.company:
            parser.error("company name is required when using an LLM provider")

    print("Company Employee Generator")
    print("==========================\n")

    # Resolve company profile
    if args.provider == "none":
        try:
            profile = get_preset(args.industry)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"Using built-in preset: {profile.industry}")
    else:
        agent = CompanyAgent(args.company, provider=args.provider)
        try:
            profile = agent.research()
        except (RuntimeError, ValueError) as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

    print(f"\nCompany Profile:")
    print(f"  Name:        {profile.name}")
    print(f"  Industry:    {profile.industry}")
    print(f"  Departments: {', '.join(profile.departments)}")
    print(f"  Locations:   {', '.join(l['city'] for l in profile.office_locations)}")
    print(f"  Job Titles:  {len(profile.job_titles)} unique titles\n")

    print(f"Generating {args.num} employees...")
    gen = EmployeeGenerator(profile, args.num)
    employees = gen.generate()

    level_counts = {}
    for e in employees:
        level_counts[e.level] = level_counts.get(e.level, 0) + 1
    level_labels = {1: "Executives", 2: "VPs", 3: "Managers", 4: "Individual Contributors"}
    breakdown = ", ".join(
        f"{level_counts[l]} {level_labels[l]}"
        for l in sorted(level_counts)
    )
    print(f"Created {len(employees)} employees ({breakdown})\n")

    output = gen.to_csv() if args.format == "csv" else gen.to_json()

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Output written to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
