# Agentic Assistant Knowledge Base: Agent Guidelines

## Project Purpose
- Support users in coding, automation, and agentic workflows.
- Provide clear, actionable, and context-aware answers.

## General Guidelines
- Always format tables, code, and lists using markdown.
- When unsure, ask clarifying questions.
- If a command or action is potentially unsafe, require explicit user confirmation.

## Microsoft Fabric
- use the Fabric cli via terminal to run commands
- to list workspaces: `fab ls`
- to list the workspaces with their details: `fab ls -l`
- to get the users assigned to a workspace: `fab acl ls [workspacename.Workspace]
- to get the contents of a workspace: `fab ls [workspacename.Workspace]

## Terminal generic information
- if the user asks who am I or similar questions use the terminal command whoami
