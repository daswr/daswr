import sciter
import daswr
import threading,time

 

class Gui(sciter.Window):
    def __init__(self):
        super().__init__(ismain=True, uni_theme=False,debug=True,resizeable=False,size=[800,260])
        self.WIRING_THREAD=None

    def on_subscription(self, groups):
        from sciter.event import EVENT_GROUPS
        return  EVENT_GROUPS.HANDLE_SCRIPTING_METHOD_CALL


    @sciter.script
    def clickSelect(self):
        pids=daswr.selectProcessesWithClick()
        return ",".join(str(x) for x in pids)

    @sciter.script
    def listSources(self):
        l=daswr.listSources()
        out=[]
        for s in l:
            out.append({
                "name":s["name"],
                "description":s["description"]
            })
        return out

    def loop(self,mic,out,pids):
        while self.WIRING_THREAD:
            daswr.rewire(mic,pids,out)
            time.sleep(1)


    @sciter.script
    def stopStream(self):
        print("Closing stream")
        tr=self.WIRING_THREAD
        if tr:
            self.WIRING_THREAD=None
            tr.join()
        daswr.cleanup()
        print("Closed")

    @sciter.script
    def startStream(self,mic,out,pids):
        print("Starting stream")
        if self.WIRING_THREAD:
            print("Thread already started!?")
            return
        pids=pids.split(",")
        self.WIRING_THREAD=threading.Thread(target=self.loop,args=(mic,out,pids))
        self.WIRING_THREAD.start()
        print("Started!")

    @sciter.script
    def println(self,str):
        print(str)

    @sciter.script
    def listSinks(self):
        l=daswr.listSinks()
        out=[]
        for s in l:
            out.append({
                "name":s["name"],
                "description":s["description"]
            })
        return out

    @sciter.script
    def listProcesses(self):
        l=daswr.listProcesses()
        out=[]
        for title,v in l.items():
            out.append({
                "name":",".join(str(x) for x in v["pids"]),
                "description":title,
            })
        return out



frame = Gui()
frame.load_file("GUI.html")
frame.expand()
frame.run_app()
frame.stopStream()
print("Gui closed!")