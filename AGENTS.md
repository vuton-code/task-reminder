# task-reminder working notes

- Follow .specify/memory/constitution.md and specs/001-task-reminder/ before changing product rules.
- Start with IMPLEMENTATION_STATUS.md for evidence and remaining work; read only relevant files.
- Use .agents/skills/modern-web-guidance/SKILL.md for frontend changes.
- Browser baseline: Widely available. Preserve progressive enhancement and ordinary server navigation.
- Do not enable experimental/origin-trial features or add unrelated capabilities.
- Run focused tests per change and a full suite at a release checkpoint.
- Keep live providers, physical-device and human timing evidence separate from fixtures.
- Never print .env values. Local email stays fake until credentials are configured.
- Git is initialized on main; origin is https://github.com/vuton-code/task-reminder.git.
- Verify commit, push and deployment status independently; never infer deployment from a commit.
