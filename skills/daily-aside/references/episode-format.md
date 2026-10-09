# Episode and music inputs

Episode JSON fields:
- title: nonempty title
- date: YYYY-MM-DD in the user's time zone
- config: optional object with programmeName, djName, deliveryStyle, language, locale (strings); language defaults to en. Optional speechBudget is {"unit":"words" or "characters","min":integer,"max":integer}. Names are editorial guidance and must also appear in the approved script if they should be spoken.
- segments: exactly five strings. English preset: 850–1050 words; Japanese preset: 1950–2250 spoken characters. Other languages require an explicit speechBudget
- config.contentClass: public, personal or confidential; default personal. Unpaid Gemini services accept only reviewed public-only material. This is a safety declaration, not automatic anonymization.
- sources: one or more objects with label, credential-free HTTPS url, and checkedAt (ISO 8601 timestamp with time zone)

Keep actual episode data in the user's private working directory. The generic test generator creates synthetic text only; it is not an editorial example to publish.

Music credit JSON must include title, creator, source, license, changes as nonempty strings. Record the verified source and license URLs where available. Describe looping, level changes, fades, and mixing in changes. Put any rights evidence and additional attribution in the credit, and include music attribution with every delivered episode. Selecting a license string does not establish that the user has those rights.

Example (schematic; not real music):

    {"title":"User-provided piano track","creator":"Actual composer","source":"Verified source URL or provenance","license":"Verified license and URL","changes":"Looped, level-adjusted, ducked, faded and mixed with narration"}

Cache identity includes all five exact segments, model, voice, delivery style, and a schema version. Changing any of those starts a new cache; a name change with unchanged spoken text does not. Cache files never belong inside the distributed skill. Completed chunks are checked by SHA-256 and WAV structure before reuse. The cache does not prove pronunciation accuracy or provenance; review the listening result.
