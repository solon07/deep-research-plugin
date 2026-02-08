---
name: init
description: Bootstrap the deep research workspace directory structure and verify the environment is configured correctly.
disable-model-invocation: true
---

Initialize the deep research workspace.

## Instructions

1. Create the `.deep-research/` directory structure if it doesn't exist:
   ```
   .deep-research/
   └── runs/
   ```

2. Verify the environment:
   - Check that Python 3 is available
   - Check that the plugin scripts are accessible and executable
   - Check if Agent Teams are enabled (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` environment variable)

3. Report the status:
   - Workspace path
   - Python version
   - Agent Teams availability
   - Any existing runs found
   - Any configuration issues

If $ARGUMENTS contains a topic, also initialize a new run for that topic using:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/dr_init_run.py "$ARGUMENTS"
```
