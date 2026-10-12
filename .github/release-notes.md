## Downloads for Windows

| File | What it is |
| --- | --- |
| `JazzPianoComposer.exe` | A single file. Download it and double-click. Takes a few seconds to open. |
| `JazzPianoComposer-windows.zip` | A portable folder. Unzip it anywhere and run `JazzPianoComposer.exe` inside. Opens faster. |
| `SHA256SUMS.txt` | Checksums to verify that your download is intact. |

No installation and no Python needed. Unzip the portable folder somewhere with a short path
(Desktop or Documents, for example): Windows cannot load it from very deeply nested folders. On macOS and Linux, run the app from source (see the README).

### ⚠️ Windows may warn you about this file

When you open the program, Windows may show **"Windows protected your PC"**, and some
antivirus tools may flag the download. **This does not mean the program contains a virus.**

It happens because the program is **not digitally signed**: a code-signing certificate is a
paid license that small free projects like this one usually do not have, so Windows cannot
identify the publisher and warns by default. Programs packaged with PyInstaller, like this
one, are a well-known source of these false alarms.

To run it: click **More info → Run anyway**.

You do not have to take this on trust:

- The complete source code is in this repository.
- These files were built by GitHub Actions directly from that source, not on a personal
  computer. The build log is public under the **Actions** tab.
- You can verify your download against `SHA256SUMS.txt`
  (`Get-FileHash JazzPianoComposer.exe` in PowerShell).
- If you would rather not run a downloaded executable at all, run the app from source.
