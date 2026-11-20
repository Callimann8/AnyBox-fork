# kernelx technical debt

Serves `kernelx.dll`.

### Functional

- [Forwards](../../../core/libs/xdll/kernelx/Forwards.def) (kernelx) - a Win32 subset forwarded to `kernel32`, assuming console and desktop semantics match; the full export list grows from import audits of real titles
  Closes when: a title's import audit lists its kernelx imports
