# cooldown-manager

per-user, per-command cooldowns for discord bots, saved to disk. no dependencies.

built after learning the hard way that bots forget everything when they restart.

## features

- cooldowns per user and per command
- `check_and_start` in one call, so there's no race between checking and starting
- `reset` for coffee-style items that clear specific cooldowns
- atomic saves: written to a temp file and swapped in, so a crash mid-save can't wipe the file
- a corrupt save file is renamed to `.corrupt` instead of crashing the bot or being overwritten
- expired entries get pruned on save, so the file doesn't grow forever
- injectable clock, which is how the tests run without waiting

## use

```python
from cooldowns import CooldownManager, format_remaining

cooldowns = CooldownManager("cooldowns.json")

@bot.tree.command()
async def daily(interaction):
    ok, left = cooldowns.check_and_start(interaction.user.id, "daily", 86400)
    if not ok:
        return await interaction.response.send_message(f"come back in {format_remaining(left)}.")
    await interaction.response.send_message("you claimed 500 coins.")
```

clearing a few cooldowns at once:

```python
cooldowns.reset(user_id, "work", "beg", "mine", "fish")
```

## test

```
python test_cooldowns.py
```
