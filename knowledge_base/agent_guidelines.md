## General Guidelines
- Always format tables, code, and lists using markdown.
- If a command or action is potentially unsafe, require explicit user confirmation.

## Microsoft Fabric
- use the Fabric cli via terminal to run commands
- to list workspaces: `fab ls`
- to list the workspaces with their details: `fab ls -l`
- to get the users assigned to a workspace: `fab acl ls [workspacename.Workspace]
- to get the contents of a workspace: `fab ls [workspacename.Workspace]

## Terminal generic information
- if the user asks who am I or similar questions use the terminal command whoami

## Browser use
- For search the internet always use the "browser_use_agent". Before doing so, inform the user this feature is experimental and ask confirmation before using it