import pulsectl,re,psutil
from xdo import Xdo
import xutil
import getpass

PREFIX="daswr"
PULSE=pulsectl.Pulse(PREFIX) 
FIND_SINK_NAME_IN_ARGS_RE= re.compile('sink_name\s*=\s*([A-Z0-9_\.\-]+)', re.IGNORECASE)
FIND_SRC_IN_ARGS_RE= re.compile('source\s*=\s*([A-Z0-9_\.\-]+)', re.IGNORECASE)
FIND_SINK_IN_ARGS_RE= re.compile('sink\s*=\s*([A-Z0-9_\.\-]+)', re.IGNORECASE)
FIND_SOURCE_NAME_IN_ARGS_RE= re.compile('source_name\s*=\s*([A-Z0-9_\.\-]+)', re.IGNORECASE)
XDO=Xdo()

LAST_WIRING=[]
UNLOAD_QUEUE=[]

def sendRawCmd(cmd):
    pulsesock=pulsectl.connect_to_cli(socket_timeout=1)
    pulsesock.write(cmd+"\n")
    pulsesock.flush()
    output=""
    try:
        for line in pulsesock:
            output+=line
    except: pass
    pulsesock.close()
    return output


def _getDefaultFromPacmdListing(listing):
    try:
        st=listing.index("* index: ")+len("* index: ")
        id=int(listing[st:].split("\n",1)[0])
        return id
    except:
        return 0


def findModule(filtersMatches):
    for m in PULSE.module_list():
        module_args=m.argument
        if not module_args:continue
        failed=False
        for f,ma in filtersMatches.items():
            res=f.search(module_args)
            if not res or res.group(1)!=ma:
                failed=True
                break
            

        if not failed:
            return m
    return None 



def listInputs():
    inputs=[]
    for i in PULSE.sink_input_list():
        props=i.proplist
        if not "application.name" in props or not "application.process.id" in props: continue
        inputs.append({
            "name":props["application.name"],
            "pid":props["application.process.id"],
            "sink":i.sink,
            "data":i,
            "index":i.index
        })
    return inputs

def getDefaultSink():
    sinksraw=sendRawCmd("list-sinks")
    i=_getDefaultFromPacmdListing(sinksraw)
    for s in listSinks():
        if s.index==i:
            return s
    return None


def listSinks():
    sinksraw=sendRawCmd("list-sinks")
    i=_getDefaultFromPacmdListing(sinksraw)

    sinks=[]
    for s in PULSE.sink_list():
        s={
            "name":s.name,
            "description":s.description,
            "index":s.index,
            "score":0
        }
        if s["index"]==i:
            s["score"]+=1
        
        desclow= s["description"].lower()
        if("use me" in desclow or "use this" in desclow):
            s["score"]+=2

        if len(LAST_WIRING)>1 and LAST_WIRING[2]==s["name"]:
            s["score"]+=4
        sinks.append(s)
    sinks.sort(reverse=True,key=lambda a: a["score"])
    return sinks



def listSources():
    sourcesraw=sendRawCmd("list-sources")
    i=_getDefaultFromPacmdListing(sourcesraw)
    sources=[]
    for s in PULSE.source_list():
        s={
            "name":s.name,
            "description":s.description,
            "index":s.index,
            "mute":s.mute,
            "volumes":s.volume,
            "score":0
        }
        
        if s["index"]==i:
            s["score"]+=1

        desclow= s["description"].lower()
        if("use me" in desclow or "use this" in desclow):
            s["score"]+=2

        if len(LAST_WIRING)>0 and LAST_WIRING[0]==s["name"]:
            s["score"]+=4

        sources.append(s)
    sources.sort(reverse=True,key=lambda a: a["score"])
    return sources


def _getAllProcesses(processes,parent):
    processes.append(parent)
    for c in psutil.Process(pid=parent).children(recursive=True):
        processes.append(c.pid)   

def listProcesses():
    processes={}
    windowsList=xutil.getWindows()
    pids=[]
    for proc in psutil.process_iter():
        _getAllProcesses(pids,proc.pid)

    for proc in pids:
        try:
            pinfo = psutil.Process(pid=proc).as_dict(attrs=['pid', 'name',"username"])
            if pinfo["username"]!=getpass.getuser(): continue

            windows=xutil.getWindowsByPid(pinfo["pid"],windowsList)
            # windows=XDO.search_windows(pid=pinfo["pid"])
            if len(windows)>0:
                for win in windows:
                    # winTitleB=XDO.get_window_name(win)
                    # winTitle="???"
                    # if winTitleB:    winTitle=str(XDO.get_window_name(win),'utf-8')
                    winTitle=win["name"]
                    
                    if not winTitle in processes:
                        processes[winTitle]={
                            "pids":[],
                            "title":winTitle,
                            "names":[]
                        }                    
                    if not pinfo["pid"] in processes[winTitle]["pids"]: processes[winTitle]["pids"].append(pinfo["pid"])
                    if not pinfo["name"] in processes[winTitle]["names"]: processes[winTitle]["names"].append(pinfo["name"])          
            else:
                processes[pinfo["name"]]={
                    "pids":[pinfo["pid"]],
                    "title":pinfo["name"],
                    "names":[pinfo["name"]]
                }              
        except:
            pass
    return processes



def deleteSink(name):
    module=findModule({FIND_SINK_NAME_IN_ARGS_RE:name})
    if not module:return
    print("Unload module",module.index)
    PULSE.module_unload(module.index)

def deleteLoopback(src,dest):
    module=findModule({FIND_SRC_IN_ARGS_RE:src,FIND_SINK_NAME_IN_ARGS_RE:dest})
    if not module:return
    PULSE.module_unload(module.index)

def getSink(name):
    sinks=PULSE.sink_list()
    for sink in sinks:
        if sink.name==name:
            return sink
    return None

def getOrCreateNullSink(name):
    sink=getSink(name)
    if not sink:
        print(name,"doesn't exist. Create")
        moduleIndex=PULSE.module_load("module-null-sink","sink_name="+name)
        UNLOAD_QUEUE.append(lambda : PULSE.module_unload(moduleIndex))
        sink=getSink(name)
    return sink
   
def getOrCreateLoopBack(src,dest):
    module=findModule({FIND_SRC_IN_ARGS_RE:src,FIND_SINK_IN_ARGS_RE:dest})
    if not module:
        print(src,"-",dest,"not found. Create")
        moduleIndex=PULSE.module_load("module-loopback","source="+src+" sink="+dest)
        UNLOAD_QUEUE.append(lambda : PULSE.module_unload(moduleIndex))
        module=findModule({FIND_SRC_IN_ARGS_RE:src,FIND_SINK_IN_ARGS_RE:dest})
    else:
        print("Found loopback at",src,"-",dest)
    return module

def deleteSource(sourceName):
    module=findModule({ FIND_SOURCE_NAME_IN_ARGS_RE:sourceName})
    PULSE.module_unload(module.index)

def getOrCreateSource(sink,sourceName):
    FIND_SOURCE_NAME_IN_ARGS_RE
    module=findModule({ FIND_SOURCE_NAME_IN_ARGS_RE:sourceName})
    if not module:
        print("Create source",sourceName)
        moduleIndex=PULSE.module_load("module-remap-source","master="+sink+" source_name="+sourceName+"   source_properties=device.description="+sourceName )
        UNLOAD_QUEUE.append(lambda : PULSE.module_unload(moduleIndex))
        module=findModule({ FIND_SOURCE_NAME_IN_ARGS_RE:sourceName})
    else:
        print("Source already exists",sourceName)
    return module

def cleanup():
    for l in UNLOAD_QUEUE:
        l()
    UNLOAD_QUEUE.clear()


def connectAppToSink(pids,sinkName,sinkId=None,unload=False):
    ipids=[]
    for p in pids:
        ipids.append(int(p))
    pids=ipids
    destSink=sinkId if sinkId else getOrCreateNullSink(sinkName).index

    print("Prepare to connect  ",pids," to ",destSink,unload)


    app_inputs=[]
    inputs=listInputs()
    for i in inputs:
        if int(i["pid"]) in pids :
            app_inputs.append(i)

    for i in app_inputs:
        if "sink" in i and i["sink"] == destSink:
            print("App ",i["index"]," already connected to sink")
            continue
        PULSE.sink_input_move(i["index"],destSink)
        if not unload: 
            print("Connect ",i["index"]," to ",destSink)
            UNLOAD_QUEUE.append(lambda: connectAppToSink(pids,sinkName=None,sinkId=destSink,unload=True)  )
        else:
            print("Connect ",i["index"]," to ",destSink," (unload)")



def selectProcessesWithClick():
    out=[]
    parentPids=xutil.getWinByClick()
    try:
        for parentPid in parentPids:
            _getAllProcesses(out,parentPid)
            # for c in psutil.Process(pid=parentPid).children(recursive=True):
            #     out.append(c.pid)   
    except: 
        pass
    return out

def rewire(mic,app_pids,out,loadAndSave=None):
    global LAST_WIRING
    if loadAndSave:
        LAST_WIRING=loadAndSave[0]()
    else: LAST_WIRING=[]

    app_pids=sorted(app_pids)
    if (len(LAST_WIRING)>=2) and (LAST_WIRING[0]!=mic or LAST_WIRING[1]!=app_pids or LAST_WIRING[2]!=out):
        print("Wiring changed. Reset!")
        cleanup()
        LAST_WIRING[0]=mic
        LAST_WIRING[1]=app_pids
        LAST_WIRING[2]=out
        loadAndSave[1](LAST_WIRING)

    getOrCreateNullSink(PREFIX+"_AppProxy")
    getOrCreateNullSink(PREFIX+"_MicProxy")
    getOrCreateNullSink(PREFIX+"_DiscordMix")

    

    getOrCreateLoopBack(mic,PREFIX+"_MicProxy")
    getOrCreateLoopBack(PREFIX+"_MicProxy.monitor",PREFIX+"_DiscordMix")

    getOrCreateLoopBack(PREFIX+"_AppProxy.monitor",PREFIX+"_DiscordMix")
    getOrCreateLoopBack(PREFIX+"_AppProxy.monitor",out)

    getOrCreateSource(PREFIX+"_DiscordMix.monitor","DiscordMixedDevice")

    if len(app_pids)>0: 
        connectAppToSink(app_pids,PREFIX+"_AppProxy")

