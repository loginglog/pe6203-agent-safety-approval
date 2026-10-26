# OpenRouter account setup for this project

OpenRouter is a website and API service. No desktop application or additional SDK installation is needed for this project; the project uses its pinned OpenAI SDK 3.31.0 against OpenRouter's endpoint.

1. Register and sign in at https://openrouter.ai/ using an available sign-up option.
2. Open https://openrouter.ai/settings/credits. Purchase a small initial balance, for example USD 5 of credits if offered by checkout, rather than committing the full project allowance at once. Check the total shown before paying; platform fees and applicable taxes are separate from model token usage. Keep automatic recharge off for this bounded project.
3. Open https://openrouter.ai/settings/keys and create a dedicated inference API key, named for example pe6203-experiment. Set a cumulative credit limit no greater than USD 20; do not accept a higher onboarding default or an automatically resetting allowance for this total-budget project.
4. Enter the key locally as the value of OPENAI_COMPATIBLE_API_KEY in the repository-root .env file. Keep OPENAI_COMPATIBLE_BASE_URL=https://openrouter.ai/api/v1 unchanged. The template has already been created with an empty key and is Git-ignored.
5. Tell the assistant only that local configuration is complete. Do not paste the key into chat or share a screenshot containing it. Never upload .env to GitHub.

Key creation does not itself run the experiment. The project's per-task USD 0.10 program-side limit is distinct from the key's cumulative limit and the available account balance. Budget-accounting records must preserve unknown charges; this page does not claim a provider billing guarantee.

The user has requested the old draft's task/model/k/runtime settings for the first exploratory round. See configs/first_round_experiment.json for the copied settings and unresolved execution issues. Task28 is development-used; the old draft's candidate version differs from the current selector; its injection setup is unfinished and not supported for live execution by the current runner. No model, policy version, test condition, or result is silently substituted by this onboarding guide.

Official sources checked October 19, 2026:

- Quickstart: https://openrouter.ai/docs/quickstart
- API key creation and credit limits: https://openrouter.ai/docs/api_reference/authentication
- Credits and platform fees: https://openrouter.ai/pricing
