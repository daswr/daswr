import pulsectl,re,psutil,json


PREFIX="daswr"
PULSE=pulsectl.Pulse(PREFIX) 
FIND_SINK_NAME_IN_ARGS_RE= re.compile('sink_name=([A-Z0-9_]+)', re.IGNORECASE)
FIND_SRC_IN_ARGS_RE= re.compile('source=([A-Z0-1_]+)\.monitor', re.IGNORECASE)
FIND_SINK_IN_ARGS_RE= re.compile('sink=([A-Z0-9_]+)', re.IGNORECASE)

# LOADED_MODULES=[]

def getSinkByName(name):
    sinks=PULSE.sink_list()
    for sink in sinks:
        if(sink.name==name):
            return sink
    return None

def findModuleIdBySinkName(name):
    for m in PULSE.module_list():
        a=m.argument
        if not a:continue
        sink_name_reo=FIND_SINK_NAME_IN_ARGS_RE.search(a)
        if not sink_name_reo: continue
        sink_name=sink_name_reo.group(1)
        if sink_name==name: return m.index
    return None


def findModuleIdBySourceAndSink(src,sink):
    for m in PULSE.module_list():
        a=m.argument
        if not a:continue
        sink_reo=FIND_SINK_IN_ARGS_RE.search(a)
        source_reo=FIND_SRC_IN_ARGS_RE.search(a)
        if not source_reo or not sink_reo: continue
        sink_name=sink_reo.group(1)
        source_name=source_reo.group(1)
        if sink_name==sink and source_name==src: return m.index
    return None

def deleteSinkByName(name):
    module_id=findModuleIdBySinkName(name)
    if not module_id:return
    print("Unload module",module_id)
    PULSE.module_unload(module_id)

def deleteLoopBackBySourceAndDest(src,dest):
    module_id=findModuleIdBySourceAndSink(src,dest)
    PULSE.module_unload(module_id)

def getOrCreateNullSink(name):
    sink=getSinkByName(name)
    if not sink:
        print(name,"doesn't exist. Create")
        PULSE.module_load("module-null-sink","sink_name="+name)
        # LOADED_MODULES.append(name)
        sink=getSinkByName(name)
    return sink
   

def getOrCreateLoopBack(src,dest):
    module_id=findModuleIdBySourceAndSink(src,dest)
    if not module_id:
        print(src,"-",dest,"not found. Create")
        module_id= PULSE.module_load("module-loopback","source="+src+" sink="+dest)
    else:
        print("Found loopback at",module_id)
    return module_id

def getSources():
    sources=[]
    for s in PULSE.source_list():
        sources.append(s)
    return sources


def getSinks():
    sinks=[]
    for s in PULSE.sink_list():
        sinks.append(s)
    return sinks


def listInputs():
    inputs=[]
    for i in PULSE.sink_input_list():
        props=i.proplist
        if not "application.name" in props or not "application.process.id" in props: continue
        inputs.append({
            "name":props["application.name"],
            "pid":props["application.process.id"],
            "data":i,
            "index":i.index
        })
    return inputs

def getOrCreateSource(sink,sourceName):
    # find if exists
    module_id= PULSE.module_load("module-remap-source","master="+sink+" source_name="+sourceName+"   source_properties=device.description="+sourceName )


# application.process.id
def rewire(mic,app_pids,out):

    appSink=getOrCreateNullSink(PREFIX+"_AppProxy")
    getOrCreateNullSink(PREFIX+"_MicProxy")
    getOrCreateNullSink(PREFIX+"_DiscordMix")

    hasPids=app_pids and len(app_pids)>0
    app_inputs=[]
    if hasPids:
        inputs=listInputs()
        for i in inputs:
            if int(i["pid"]) in app_pids :
                app_inputs.append(i["index"])
        


    getOrCreateLoopBack(mic,PREFIX+"_MicProxy")
    getOrCreateLoopBack(PREFIX+"_MicProxy.monitor",PREFIX+"_DiscordMix")

    getOrCreateLoopBack(PREFIX+"_AppProxy.monitor",PREFIX+"_DiscordMix")
    getOrCreateLoopBack(PREFIX+"_AppProxy.monitor",out)

    for i in app_inputs:
        print("Link ",i," to ",appSink.index)
        PULSE.sink_input_move(i,appSink.index)

    getOrCreateSource(PREFIX+"_DiscordMix.monitor","DiscordMixedDevice")


def findPidsByName(name):
    pids=[]
    for proc in psutil.process_iter():
        pinfo = proc.as_dict(attrs=['pid', 'name'])
        if pinfo["name"].lower()==name.lower():
            pids.append(pinfo["pid"])
    return pids

print(getSources())
print(getSinks())
#print(getProcesses()) #todo

APP_NAME="chrome"
APP_PIDS= findPidsByName(APP_NAME)
MIC_ID="mic_denoised_out.monitor"
OUT_ID="alsa_output.pci-0000_00_1b.0.analog-stereo"
rewire(MIC_ID,APP_PIDS,OUT_ID)
