# Contributing to PrintMoney

First off, thank you for considering contributing to PrintMoney! It's people like you that make open-source software great.

## Code of Conduct

This project and everyone participating in it is governed by the [PrintMoney Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the [issue list](https://github.com/cibi-dev/print-money/issues) as you might find out that you don't need to create one. When creating an issue, please use our **Bug Report** template and include as many details as possible:

* **Use a clear and descriptive title**.
* **Describe the exact steps to reproduce the problem**.
* **Provide logs**: Check `%APPDATA%\PrintMoney\printmoney.log` for relevant traceback information.
* **Specify your OS and Python version** (e.g., Windows 11, Python 3.11).

### Suggesting Enhancements

Feature requests are welcome! Use our **Feature Request** issue template and explain:

* The specific problem or pain point you're trying to solve.
* Why this feature would be useful to most 3D printing business owners.
* Any mockup or workflow ideas.

### Pull Requests

1. **Fork the repo** and create your branch from `main`:
   ```bash
   git checkout -b feature/my-new-feature
   ```
2. **Set up your local virtual environment**:
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt -r requirements-build.txt
   ```
3. **Follow the code style**:
   - PEP 8 guidelines for Python code.
   - All database access should go through context managers in `db_manager.py` with parameterization (no raw string interpolation).
   - Never perform blocking disk I/O or network requests inside the main UI loop — use `threading.Thread` and communicate back using `self.after()`.
   - Ensure strings intended for the UI use `utils.i18n.T()` for bilingual support (ES/EN).
4. **Run the test suite**:
   ```bash
   python -m unittest tests_atomic_io.py tests_regression.py
   ```
   All tests must pass before submitting.
5. **Commit your changes** following conventional commit messages:
   ```bash
   git commit -m "feat(inventory): add low stock notification sound"
   ```
6. **Push to your fork and submit a PR** against `main`.

## Development Guidelines

- **Database Changes**: Always increment `SCHEMA_VERSION` in `db_manager.py` and provide an incremental migration in `_migrar_esquema()`. Never break backwards compatibility with existing SQLite files.
- **Window Management**: Explicitly assign `parent=self` or `parent=self.winfo_toplevel()` to modal dialogs and `messagebox` calls to prevent focus lock on Windows.
- **Data Safety**: Write state files using `utils.atomic_io.escribir_json_atomico` to avoid file corruption on unexpected shutdowns.

Thank you for contributing! 🚀
