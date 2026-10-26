REPO: ${REPO}
PR NUMBER: ${PR_NUMBER}

Read the diff with `gh pr diff` and decide whether it touches security.

It does when it changes how the code handles untrusted input, such as vendor responses and
streams, secrets, API keys, the headers and URLs sent to vendors, network requests, retries,
logs, file paths, processes, permissions, dependencies or CI workflows.

Answer true when unsure.
