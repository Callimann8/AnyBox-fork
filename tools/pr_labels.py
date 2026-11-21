import argparse
import json
import re
import subprocess
import sys

FIXES_LABEL = "fixes issue"
UNBLOCKS_LABEL = "unblocks title"
MANAGED = {FIXES_LABEL, UNBLOCKS_LABEL}
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
UNBLOCKS = re.compile(r"^\s*(?:-\s*\[[ xX]\]\s*)?Unblocks:(.*)$", re.MULTILINE | re.IGNORECASE)
TITLE_ID = re.compile(r"\b[0-9A-Fa-f]{8}\b")
QUERY = """
query($owner: String!, $name: String!, $number: Int!) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $number) {
      number body state
      closingIssuesReferences { totalCount }
      labels(first: 100) { nodes { name } }
    }
  }
}
"""


def title_ids(body):
    text = COMMENT.sub("", body or "")
    found = []
    for line in UNBLOCKS.findall(text):
        found += [match.upper() for match in TITLE_ID.findall(line)]
    return sorted(set(found))


def labels_for(body, closes_issues, current):
    wanted = set()
    if closes_issues:
        wanted.add(FIXES_LABEL)
    if title_ids(body):
        wanted.add(UNBLOCKS_LABEL)
    current = set(current) & MANAGED
    return sorted(wanted - current), sorted(current - wanted)


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True, check=True).stdout


def pull(repo, number):
    owner, name = repo.split("/", 1)
    data = json.loads(gh("api", "graphql", "-f", f"query={QUERY}", "-f", f"owner={owner}", "-f", f"name={name}", "-F", f"number={number}"))
    pr = data["data"]["repository"]["pullRequest"]
    return {"number": pr["number"], "body": pr["body"], "state": pr["state"],
            "closes": pr["closingIssuesReferences"]["totalCount"] > 0, "labels": [label["name"] for label in pr["labels"]["nodes"]]}


def open_numbers(repo):
    return [int(line) for line in gh("pr", "list", "-R", repo, "--state", "open", "-L", "1000", "--json", "number", "--jq", ".[].number").split()]


def process(repo, number, dry_run):
    pr = pull(repo, number)
    if pr["state"] != "OPEN":
        return
    add, remove = labels_for(pr["body"], pr["closes"], pr["labels"])
    if not add and not remove:
        return
    plan = [f"+{label}" for label in add] + [f"-{label}" for label in remove]
    print(f"#{number}: {' '.join(plan)}")
    if dry_run:
        return
    args = ["pr", "edit", str(number), "-R", repo]
    if add:
        args += ["--add-label", ",".join(add)]
    if remove:
        args += ["--remove-label", ",".join(remove)]
    gh(*args)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Label pull requests from their description: fixes issue, unblocks title.")
    which = parser.add_mutually_exclusive_group(required=True)
    which.add_argument("--pr", type=int, help="label one pull request")
    which.add_argument("--all", action="store_true", help="label every open pull request")
    parser.add_argument("--repo", required=True, help="owner/name")
    parser.add_argument("--dry-run", action="store_true", help="print the changes without making them")
    args = parser.parse_args(argv)
    failed = []
    for number in ([args.pr] if args.pr else open_numbers(args.repo)):
        try:
            process(args.repo, number, args.dry_run)
        except subprocess.CalledProcessError as error:
            print(f"cannot label #{number}: {(error.stderr or '').strip()}", file=sys.stderr)
            failed.append(number)
    if failed:
        sys.exit(f"{len(failed)} pull requests not labeled: {', '.join(f'#{number}' for number in failed)}")


if __name__ == "__main__":
    main()
