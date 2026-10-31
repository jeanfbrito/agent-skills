---
name: proxmox-lxc-service
description: "Deploys native Proxmox LXC services for requests such as 'deploy in LXC', 'suba um serviço', or 'como fizemos com ai-memory'."
---

# Native services in Proxmox LXC

Deploy only the requested service. This skill grants no infrastructure permissions.
Use native installation and systemd when the application supports them.
Do not enable nesting, privileged mode, or Docker without a separate need and authorization.

## 1. Establish scope

- Record the requested service and the source of deployment authorization.
- Separate guest creation, router changes, persistent SSH, provider enrollment, and paid calls.
- Do not reuse permission from a previous deployment.
- Preserve existing guests, their credentials, and their network settings.
- Consult available historical memory when this work continues a previous deployment.
- Resolve ordinary choices from current evidence. Ask only for material missing decisions or permissions.

## 2. Inspect before creating

Run the read-only inventory helper with the existing SSH alias:

```sh
python3 ~/Github/agent-skills/proxmox-lxc-service/check.py preflight --host <ssh-alias>
```

It checks Proxmox version, guest inventory, capacity, templates, and the next available ID.
It uses BatchMode and a bounded timeout. It does not accept passwords or change SSH authorization.
If authentication fails, report the error. Never extract passwords from transcripts.
Persistent administrative SSH requires separate approval. Keep private keys on their source machine.

Inspect the selected bridge, storage, template, and protected guests with bounded read-only commands.
Check the guest ID immediately before creation. Do not overwrite an existing guest.
Check the published stable release, runtime requirements, native install method, and artifact integrity.
The default source branch is not proof of a published stable release.
Inspect startup, authentication, data paths, and backup support before provisioning.

## 3. Create and install

Use an unprivileged LXC and explicit resource limits within measured host capacity.
Use a dedicated non-root account for the application.
Use verified release artifacts or a pinned package from the official registry.
Give installation scripts an explicit PATH, including the actual runtime directory.
A failed final version check does not prove installation failed. Inspect the artifact before reinstalling.
Inspect package lifecycle warnings. Do not enable all installation scripts to hide one missing runtime repair.
Run long installation commands in the background with logs that exclude secrets.

For systemd failures, inspect failed units and host denials before changing security settings.
Apply only the demonstrated guest-level compatibility change.
A generic nesting warning does not establish that nesting is necessary.
Keep the outer container isolation intact.

## 4. Configure address, access, and persistence

Load the installed `opnsense` skill for OPNsense changes. Do not duplicate its router procedure here.
For another router, use its documented workflow.
Check reservations, leases, dynamic pools, and live address evidence before choosing an IP.
No ping response alone does not prove an address is free.
Exclude a reserved address from dynamic allocation when the DHCP implementation requires it.
Back up router configuration and prove that unrelated reservations remain unchanged.
Renew only the target guest's lease. Check the address from both the guest and the client.

Use the user's authorized access policy. Keep protected access unless the user requests open access.
An open-mode request applies only to this service, not every LAN service.
Explain that open mode permits all callers who can reach the listener.
Do not describe open mode as a subnet restriction unless a network control enforces that restriction.
Do not add WAN forwarding, tunnels, or public DNS without authorization.

Bind to loopback during bootstrap when possible. Test the chosen policy before LAN exposure.
Use supported application settings. Preserve credentials when disabling their requirement.
Store credentials in owner-only files, never in prompts, logs, or committed configuration.
Keep application data and encryption keys outside the versioned installation directory.
Enable systemd startup and define restart, stop, and filesystem permissions.

## 5. Check the deployed artifact

Test from the real client, not only from inside the guest.
Choose routes that represent the dashboard and API contract. Exclude public health and login routes from protected-route checks.
The HTTP helper performs GET requests only. Use it only on routes documented as read-only.
It sends no inference requests and follows no redirects.

For open access:

```sh
python3 ~/Github/agent-skills/proxmox-lxc-service/check.py http \
  --url http://<guest-ip>:<port> --expect open \
  --path /dashboard --path /api/settings --path /v1/models
```

For protected access:

```sh
python3 ~/Github/agent-skills/proxmox-lxc-service/check.py http \
  --url http://<guest-ip>:<port> --expect protected --path /v1/models \
  --credential-file /private/path/headers.json
```

The optional credential file is an owner-only JSON object of HTTP headers.
For example, it can contain an Authorization header or an application session cookie.
Create credentials through the application's supported login or key workflow.
Never put their values in command arguments. Use separate runs for routes with different credential types.
The helper first checks requests without credentials. Then it checks the supplied credentials, if any.
Protected mode without that file proves denial only, not successful authentication.
A redirect is a failed check, not proof that the login page or target route works.

Check invalid credentials when applicable. Check a real browser for interactive or visual behavior.
Check data and credentials after an authorized service restart and target-guest reboot.
Do not reboot the host or unrelated guests.
Use the application's online backup method, or stop its writer for a consistent archive.
Include encryption keys required for recovery. Protect archives as credentials.
Restore into a separate destination. Check database integrity and application recovery separately.
Do not call archive extraction a replacement-host recovery test.
Measure guest RAM, swap, disk, and service memory. Name the measurement method.
Recheck protected guests. Record untested inference, load, browser, or recovery behavior as UNVERIFIED.

## 6. Report and retain evidence

Read `~/Github/agent-skills/shared/tone.md` before drafting text for other people.
Use measured numbers, frame gaps as scope, avoid a defensive lead, and anonymize customer details.
Show the exact draft for approval before publishing reports externally.
An authorized deployment does not authorize posting its report or committing its scripts.

Record the guest ID, version, address, access policy, service unit, data path, and backup method.
Report the actual checks and their limits. Do not print credentials.
Keep operational state in the project's ignored working directory.
Keep any optional per-user skill configuration in a gitignored `local-config.yml`.
Do not ship real host addresses, credentials, guest IDs, or protected-guest lists in this skill.

## Local helper tests

```sh
python3 -m unittest discover -s ~/Github/agent-skills/proxmox-lxc-service/tests -v
```

These tests use a local HTTP fixture and mocked SSH. They do not check a live deployment.
