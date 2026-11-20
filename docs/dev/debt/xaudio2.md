# xaudio2 technical debt

Serves `xaudio2_9.dll`.

### Functional

- [Forwards](../../../core/libs/xdll/xaudio2/Forwards.def) (xaudio2) - forwarded to the host's XAudio2 2.9; console-only formats (XMA2) and hardware voices are not decoded or emulated, and the console DLL name and export list are unverified
  Closes when: a title's import audit confirms the DLL name and exports
