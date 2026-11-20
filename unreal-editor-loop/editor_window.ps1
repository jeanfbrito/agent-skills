<#
editor_window.ps1: see, capture and click the windows of the open Unreal editor, without a desktop screenshot.
  -Action list                                  visible window titles of the UnrealEditor process
  -Action shot  -Title <t> -Out <png>           capture only that window (PrintWindow)
  -Action click -Title <t> -X <x> -Y <y>        real click at window pixel x,y (from the shot), cursor restored
Slate hit-tests the real cursor: a posted WM_LBUTTONDOWN does nothing, so the click moves the cursor for ~0.4 s.
Run: powershell -NoProfile -ExecutionPolicy Bypass -File editor_window.ps1 -Action list
#>
param([ValidateSet("list","shot","click")][string]$Action="list",[string]$Title,[string]$Out,[int]$X,[int]$Y)
Add-Type -AssemblyName System.Drawing
Add-Type @'
using System;using System.Text;using System.Collections.Generic;using System.Runtime.InteropServices;
public class UEWin{
 delegate bool P(IntPtr h,IntPtr l);
 [DllImport("user32")] static extern bool EnumWindows(P p,IntPtr l);
 [DllImport("user32")] static extern int GetWindowText(IntPtr h,StringBuilder s,int n);
 [DllImport("user32")] static extern bool IsWindowVisible(IntPtr h);
 [DllImport("user32")] static extern uint GetWindowThreadProcessId(IntPtr h,out uint p);
 [DllImport("user32")] public static extern bool GetWindowRect(IntPtr h,out R r);
 [DllImport("user32")] public static extern bool PrintWindow(IntPtr h,IntPtr dc,uint f);
 [DllImport("user32")] public static extern bool SetForegroundWindow(IntPtr h);
 [DllImport("user32")] public static extern bool SetCursorPos(int x,int y);
 [DllImport("user32")] public static extern bool GetCursorPos(out PT p);
 [DllImport("user32")] public static extern void mouse_event(uint f,uint x,uint y,uint d,UIntPtr e);
 public struct R{public int L,T,Ri,B;} public struct PT{public int X,Y;}
 public static List<KeyValuePair<IntPtr,string>> List(HashSet<uint> pids){
  var r=new List<KeyValuePair<IntPtr,string>>();
  EnumWindows((h,l)=>{uint p;GetWindowThreadProcessId(h,out p);
   if(pids.Contains(p)&&IsWindowVisible(h)){var s=new StringBuilder(256);GetWindowText(h,s,256);r.Add(new KeyValuePair<IntPtr,string>(h,s.ToString()));}
   return true;},IntPtr.Zero);
  return r;}
}
'@
$pids=New-Object 'System.Collections.Generic.HashSet[uint32]'
Get-Process UnrealEditor -ErrorAction SilentlyContinue | % { [void]$pids.Add([uint32]$_.Id) }
if($pids.Count -eq 0){"no UnrealEditor process";exit 1}
$wins=[UEWin]::List($pids)
if($Action -eq "list"){ $wins | % { "WIN: [$($_.Value)]" }; exit 0 }
$h=($wins | ? { $_.Value -eq $Title } | Select-Object -First 1).Key
if(-not $h){"no editor window titled [$Title]";exit 1}
$r=New-Object UEWin+R; [void][UEWin]::GetWindowRect($h,[ref]$r)
if($Action -eq "shot"){
 $b=New-Object System.Drawing.Bitmap ($r.Ri-$r.L),($r.B-$r.T); $g=[System.Drawing.Graphics]::FromImage($b)
 $dc=$g.GetHdc(); [void][UEWin]::PrintWindow($h,$dc,2); $g.ReleaseHdc($dc); $b.Save($Out)
 "saved $Out $($b.Width)x$($b.Height)"; exit 0 }
$old=New-Object UEWin+PT; [void][UEWin]::GetCursorPos([ref]$old)
[void][UEWin]::SetForegroundWindow($h); Start-Sleep -Milliseconds 200
[void][UEWin]::SetCursorPos($r.L+$X,$r.T+$Y); Start-Sleep -Milliseconds 150
[UEWin]::mouse_event(2,0,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 80; [UEWin]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
Start-Sleep -Milliseconds 150; [void][UEWin]::SetCursorPos($old.X,$old.Y)
"clicked [$Title] at $X,$Y"
