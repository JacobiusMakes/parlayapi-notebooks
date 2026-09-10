# Privacy

Demo mode uses fictional local data and makes no network requests.

In live mode, this plugin sends the user's ParlayAPI key in an HTTPS header and the selected sport, bookmaker and market to https://parlay-api.com. Provider credential validation sends the key to the same service's no-credit key-check endpoint. Account/key-check response details are discarded; only the validity boolean is used.

The plugin does not persist or log keys, account information, participant names or raw odds. It parses source rows in memory and returns only coverage counts, clock summaries and diagnostic messages. It sends no information to another service, language model, analytics endpoint or webhook. There are no payment, bet-execution or account-write operations.

ParlayAPI receives these API requests under its service policy: https://parlay-api.com/privacy . Dify stores provider credentials and may retain invocation parameters and summary outputs under the workspace operator's configuration; consult your Dify installation's policy. Installing a tool in a shared or publicly exposed workflow changes who can see summary outputs, so keep account use private.

The user controls the API key and can revoke it through their ParlayAPI account. Remove the provider credential from Dify to stop future live access. Support: https://github.com/JacobiusMakes/ParlayAPI/issues .
