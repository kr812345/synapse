# Contributing to Synapse OS

First off, thank you for considering contributing to Synapse OS! It's people like you that make Synapse OS such a great open-source tool. 

## 1. Where do I go from here?

If you've noticed a bug or have a feature request, make sure to check our [Issues](../../issues) tab to see if someone else in the community has already created a ticket. If not, go ahead and make one! 

## 2. Setting up the Development Environment

1. Fork the repo on GitHub.
2. Clone the project to your own machine.
3. Create a Python virtual environment: `python3 -m venv .venv`
4. Activate the virtual environment: `source .venv/bin/activate`
5. Install dependencies: `pip install -r requirements.txt` (or install via `apt` if using system packages).
6. Set up PostgreSQL: You'll need `postgresql` and `postgresql-16-pgvector` installed locally to run the Memory Engine.
7. Start the API/Dashboard: Run `uvicorn api.server:app` for the WebSocket and `npm run dev` in the `dashboard/` directory for the UI.

## 3. Pull Request Process

1. Create a new branch for your feature or bugfix: `git checkout -b feature/my-awesome-feature`
2. Write your code and **add tests** to cover your changes.
3. Ensure the test suite passes locally: `python3 -m unittest discover tests/`
4. Follow the existing code style (we strictly use composition over inheritance except for `BaseAgent`).
5. Commit your changes with a descriptive commit message.
6. Push your branch and open a Pull Request against the `master` branch.
7. Ensure you fill out the provided Pull Request Template thoroughly.

## 4. Code Style & Architecture Rules

- **No Mocks in Production Code:** If you add a new `Tool` or `Agent`, it must interface with a real API or service.
- **Event-Driven:** All modules must implement the `Module` interface and communicate exclusively via the `EventBus`. Never use global state.
- **Documentation:** Always update `docs/` or `README.md` when introducing a new core concept.

Happy coding!
