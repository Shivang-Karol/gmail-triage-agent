# Contributing to Gmail Triage Agent

First off, thank you for considering contributing to the Gmail Triage Agent! It's people like you that make this agent a powerful and reliable personal assistant.

## How Can I Contribute?

### Reporting Bugs
If you find a bug:
1. Ensure the bug was not already reported by searching on GitHub under Issues.
2. If you're unable to find an open issue addressing the problem, open a new one. Be sure to include a **title and clear description**, as much relevant information as possible, and a **code sample** or an **executable test case** demonstrating the expected behavior that is not occurring.

### Suggesting Enhancements
Enhancements can range from small features to entirely new logic flows (like the planned Docker Cloud V2 migration).

1. Please open an Issue proposing the enhancement.
2. Provide a clear and detailed explanation of the feature.
3. State whether you plan to write the code yourself or are just requesting it.

### Pull Requests
1. **Fork** the repository and clone it locally.
2. Create a new branch: `git checkout -b my-branch-name`.
3. Make your changes and test them locally. (Do not commit secrets like `token.json` or `.env`!).
4. Run standard Python linting tools where applicable (e.g., `flake8`, `black`).
5. Push your branch to GitHub and open a Pull Request against the `main` branch.

## Code Style
- We follow standard PEP-8 style guidelines.
- Keep the `worker.py` logic deterministic and strictly scoped to avoid rate limit runaway scenarios.
- All new dependencies must be added to `requirements.txt`.

Happy coding!
