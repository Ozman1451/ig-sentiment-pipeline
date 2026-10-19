#!/usr/bin/env python3
import json, pathlib, sys
from openai import OpenAI

sys.path.insert(0, str(pathlib.Path.cwd() / "src"))
from schema import Tag

c = OpenAI(base_url="http://localhost:8000/v1", api_key="x")
system = (pathlib.Path.cwd() / "prompts/tagger_system.md").read_text()

canaries = [
    ("yar inka wrap is literally mid now 💀", "negative", "taste_quality"),
    ("midnight craving sorted, J&J always a W 🔥", "positive", "taste_quality"),
    ("ambiance is aesthetic af but waiting line is insane", "mixed", "ambiance_vibe"),
    ("deals kab aayengi bro? broke student here", "neutral", "price_value"),
    ("bhai cheezious ki branch dha mein kab khulegi?", "neutral", "other"),
    ("packaging 10/10 but delivery took 2 hours", "mixed", "service_speed"),
]

ok = 0
for text, exp_sent, exp_asp in canaries:
    r = c.chat.completions.create(
        model="m", temperature=0, max_tokens=200,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": text}],
        response_format={"type": "json_schema", "json_schema": {"name": "tag", "schema": Tag.model_json_schema()}}
    )
    tag = Tag.model_validate_json(r.choices[0].message.content)
    match = (tag.sentiment == exp_sent and exp_asp in tag.aspects)
    ok += int(match)
    print(f"{'✓' if match else '✗'} {text[:35]:35} → {tag.sentiment}/{tag.aspects[0] if tag.aspects else 'none'}")

print(f"\nResult: {ok}/6 canaries pass")
