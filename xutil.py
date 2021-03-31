import Xlib
import Xlib.display
from xdo import Xdo

XDO=Xdo()

def _findWindows(display,root,windows=None,winParent=None):
    if winParent: root=winParent
    if not windows:
        windows=[]
    children = root.query_tree().children    
    for win in children:
        windows.append(win)
        if winParent and winParent==root:continue
        _findWindows(display,win,windows)
    return windows


def _parseWindow(display,win):
    winName = win.get_full_property(display.intern_atom('_NET_WM_NAME'),  Xlib.X.AnyPropertyType)
    if not winName: winName=win.get_full_property(display.intern_atom('WM_NAME'),  Xlib.X.AnyPropertyType)

    winPids=win.get_full_property(display.intern_atom('_NET_WM_PID'),  Xlib.X.AnyPropertyType)
    if not winPids: winPids=win.get_full_property(display.intern_atom('WM_PID'),  Xlib.X.AnyPropertyType)
    if not winPids: winPids=win.get_full_property(display.intern_atom('STEAM_GAME'),  Xlib.X.AnyPropertyType)

    if not winName or not winPids: return None
    winName=str(winName.value.decode("utf-8"))
    winPids=winPids.value

    return {"name":winName,"pids":winPids}

def getWindows():
    o={}
    display = Xlib.display.Display()
    root = display.screen().root
    children = _findWindows(display,root)

    for win in children:
        try:
            winObj=_parseWindow(display,win)
            winName=winObj["name"]
            winPids=winObj["pids"]
            if not winName in o:
                o[winName]=[]
            for p in winPids: o[winName].append(p)
        except: 
            pass
    return o
            
def getWindowsByPid(pid,windowsList):
    o=[]
    for title,pids in windowsList.items():
        if pid in pids:
            o.append({
                "name":title,
                "pids":pids
            })
    return o

def getWinByClick():
    winId=XDO.select_window_with_click()
    if winId:
        display = Xlib.display.Display()
        win=display.create_resource_object("window",winId)
        winObj=_parseWindow(display,win)
        out=[]
        for i in winObj["pids"]:
            out.append(i)
        return out
    return []

