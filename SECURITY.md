# Security

## What this project touches

The skill sends script text to a text-to-speech provider that the user pays for, using a credential the user configures themselves. The design goals are: the agent never reads the key, no request is sent without an explicit approval flag, every attempt is recorded before transmission, nothing is retried automatically, and a local estimated-cost cap refuses requests beyond an approved limit. Offline commands and tests never read credentials or open network connections.

## Reporting a problem

If you find a way to make the client send a request without approval, exceed the local cap, leak a credential into a file, log, or command line, follow a redirect, or retry on its own, please report it privately: open a [private vulnerability report](https://github.com/LeeAkinobu/daily-aside-radio-skill/security/advisories/new) on GitHub rather than a public issue.

Never include an API key, an invoice, a private episode, or personal source material in a report. A redacted command line and the relevant `attempts.json` entries (with content removed) are enough.

## What is out of scope

The local estimate is not a billing control. It cannot see other applications using the same Google account, and the provider's invoice is authoritative. Use the provider's own billing limits as well. Provider pricing, model names, and terms change; the documentation links in `references/tts.md` are the source of truth.
