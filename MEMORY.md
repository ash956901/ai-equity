# Persistent project learnings across sessions

This document tracks persistent memory for the AI Equity Research Platform. Check here before debugging or starting new implementations.
At the end of every task, add your specific learnings, debugging solutions, and lessons learned so you don't repeat mistakes.

## Lessons Learned
- **Celery on Windows**: Always run Celery workers with `-P solo` (or `gevent`/`eventlet`). The default `prefork` pool throws `PermissionError: [WinError 5] Access is denied` due to Celery's lack of native multiprocessing support on Windows.

## Active Rabbit Holes
- (List any unresolved deeply nested issues or complex bugs being investigated)

## Resolved Issues
- (List major issues and their resolution criteria to serve as references)
