#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# generated by wxGlade 57e7a7d844ed on Wed May  1 22:57:41 2013
#

import wx, wx.richtext

# begin wxGlade: dependencies
import gettext
# end wxGlade

# begin wxGlade: extracode
# end wxGlade

import os, sys
import getpass
import socket

# Climb the tree to find out where we are
p = os.path.abspath(__file__)
t = ""
while t != "src":
    (p, t) = os.path.split(p)
    if p == "":
        print "I have no idea where I am; this is ridiculous"
        sys.exit(1)

ltlmop_root = p
sys.path.append(os.path.join(p,"src","lib"))

#######################################################
############## CONFIGURATION SECTION ##################
#######################################################
class config:
    base_spec_file = os.path.join(ltlmop_root, "src", "examples", "gumbotest", "skeleton.spec")
    #base_spec_file = os.path.join(ltlmop_root, "src", "examples", "firefighting", "firefighting.spec")
    executor_listen_port = 20000
    gumbo_gui_listen_port = 20001





#######################################################
#######################################################

import project
import mapRenderer
from specCompiler import SpecCompiler
import execute
import multiprocessing
import xmlrpclib
from SimpleXMLRPCServer import SimpleXMLRPCServer
import threading

class GumboMainFrame(wx.Frame):
    def __init__(self, *args, **kwds):
        # begin wxGlade: GumboMainFrame.__init__
        kwds["style"] = wx.DEFAULT_FRAME_STYLE
        wx.Frame.__init__(self, *args, **kwds)
        self.window_1 = wx.SplitterWindow(self, wx.ID_ANY, style=wx.SP_3D | wx.SP_BORDER | wx.SP_LIVE_UPDATE)
        self.map_pane = wx.Panel(self.window_1, wx.ID_ANY, style=wx.TAB_TRAVERSAL | wx.FULL_REPAINT_ON_RESIZE)
        self.dialogue_pane = wx.Panel(self.window_1, wx.ID_ANY)
        self.text_ctrl_dialogue = wx.richtext.RichTextCtrl(self.dialogue_pane, wx.ID_ANY, "", style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.text_ctrl_input = wx.TextCtrl(self.dialogue_pane, wx.ID_ANY, "")
        self.button_submit = wx.Button(self.dialogue_pane, wx.ID_ANY, _("Submit!"))

        self.__set_properties()
        self.__do_layout()

        self.Bind(wx.EVT_BUTTON, self.onSubmitInput, self.button_submit)
        self.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, self.onResize, self.window_1)
        # end wxGlade

        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.window_1.SetSashGravity(0.5)
        self.window_1.SetMinimumPaneSize(100)

        self.map_pane.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)
        self.mapBitmap = None

        self.robotPos = None
        self.fiducialPositions = {}

        self.map_pane.Bind(wx.EVT_PAINT, self.onPaint)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.onEraseBG)

        self.proj = project.Project()
        self.proj.loadProject(config.base_spec_file)
        self.Bind(wx.EVT_SIZE, self.onResize, self)
        self.onResize()

        # Start execution context
        print "Starting executor..."
        self.executorProcess = multiprocessing.Process(target=execute.execute_main, args=(config.executor_listen_port, self.proj.getFilenamePrefix()+".spec", None, False))
        self.executorProcess.start()

        # Connect to executor
        print "Connecting to executor...",
        while True:
            try:
                self.executorProxy = xmlrpclib.ServerProxy("http://localhost:{}".format(config.executor_listen_port), allow_none=True)
            except socket.error:
                print ".",
            else:
                break

        print

        # Start our own xml-rpc server to receive events from execute
        self.xmlrpc_server = SimpleXMLRPCServer(("localhost", config.gumbo_gui_listen_port), logRequests=False, allow_none=True)

        # Register functions with the XML-RPC server
        self.xmlrpc_server.register_function(self.handleEvent)

        # Kick off the XML-RPC server thread    
        self.XMLRPCServerThread = threading.Thread(target=self.xmlrpc_server.serve_forever)
        self.XMLRPCServerThread.daemon = True
        self.XMLRPCServerThread.start()
        print "GumboGUI listening for XML-RPC calls on http://localhost:{} ...".format(config.gumbo_gui_listen_port)

        # Register with executor for event callbacks   
        self.executorProxy.registerExternalEventTarget("http://localhost:{}".format(config.gumbo_gui_listen_port))

        # Start dialogue manager
        self.dialogueManager = BarebonesDialogueManager(self, self.executorProxy)

        # Figure out the user's name, if we can
        try:
            self.user_name = getpass.getuser().title()
        except:
            self.user_name = "User"

        # Tell the user we are ready
        self.appendLog("Hello.", "System")


    def __set_properties(self):
        # begin wxGlade: GumboMainFrame.__set_properties
        self.SetTitle(_("gumbo main window"))
        self.SetSize((883, 495))
        self.text_ctrl_input.SetFocus()
        self.button_submit.SetDefault()
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: GumboMainFrame.__do_layout
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.VERTICAL)
        sizer_3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer_2.Add(self.text_ctrl_dialogue, 1, wx.ALL | wx.EXPAND, 5)
        sizer_3.Add(self.text_ctrl_input, 1, wx.RIGHT | wx.EXPAND, 5)
        sizer_3.Add(self.button_submit, 0, 0, 0)
        sizer_2.Add(sizer_3, 0, wx.ALL | wx.EXPAND, 5)
        self.dialogue_pane.SetSizer(sizer_2)
        self.window_1.SplitVertically(self.map_pane, self.dialogue_pane)
        sizer_1.Add(self.window_1, 1, wx.EXPAND, 0)
        self.SetSizer(sizer_1)
        self.Layout()
        # end wxGlade

    def handleEvent(self, eventType, eventData):
        """
        Processes messages from the controller, and updates the GUI accordingly
        """

        if eventType in ["FREQ"]: # Events to ignore
            pass
        elif eventType == "POSE":
            self.robotPos = eventData
            wx.CallAfter(self.onPaint)
        elif eventType == "FID":
            # Update fiducial position
            self.fiducialPositions[eventData[0]] = eventData[1:]
        elif eventType == "MESSAGE":
            # Provide a way for any part of LTLMoP to give feedback
            wx.CallAfter(self.appendLog, eventData, "System")
        else:
            print "[{}] {}".format(eventType, eventData)

    def onClose(self, event):
        print "Shutting down executor..."
        try:
            self.executorProxy.shutdown()
        except socket.error:
            # Executor probably crashed
            pass

        self.xmlrpc_server.shutdown()
        self.XMLRPCServerThread.join()
        print "Waiting for executor to quit..."
        print "(If this takes more than 5 seconds it has crashed and you will need to run `killall python` for now)"
        self.executorProcess.join(5)
        # After ten seconds, just kill it
        if self.executorProcess.is_alive():
            self.executorProcess.terminate() 
            self.executorProcess.join() 
            
        event.Skip()

    def appendLog(self, message, agent=None):
        self.text_ctrl_dialogue.SetInsertionPointEnd()

        if agent is not None:
            self.text_ctrl_dialogue.BeginBold()
            self.text_ctrl_dialogue.WriteText(agent + ": ")
            self.text_ctrl_dialogue.EndBold()

        self.text_ctrl_dialogue.WriteText(message + "\n")

        self.text_ctrl_dialogue.ShowPosition(self.text_ctrl_dialogue.GetLastPosition())
        self.text_ctrl_dialogue.Refresh()

        wx.Yield()

    def onSubmitInput(self, event):  # wxGlade: GumboMainFrame.<event_handler>
        if self.text_ctrl_input.GetValue() == "":
            event.Skip()
            return
        
        user_text = self.text_ctrl_input.GetValue()

        # echo
        self.appendLog(user_text, self.user_name)

        self.text_ctrl_input.Clear()

        # response
        if self.dialogueManager is None:
            self.appendLog("Dialogue manager not initialized", "!!! Error")
        else:
            sys_text = self.dialogueManager.tell(user_text)
            self.appendLog(sys_text, "System")

        event.Skip()

    def onResize(self, event=None):  # wxGlade: GumboMainFrame.<event_handler>
        size = self.map_pane.GetSize()
        self.mapBitmap = wx.EmptyBitmap(size.x, size.y)
        self.mapScale = mapRenderer.drawMap(self.mapBitmap, self.proj.rfi, scaleToFit=True, drawLabels=mapRenderer.LABELS_ALL_EXCEPT_OBSTACLES, memory=True)

        self.Refresh()
        self.Update()

        if event is not None:
            event.Skip()

    def onEraseBG(self, event):
        # Avoid unnecessary flicker by intercepting this event
        pass

    def onPaint(self, event=None):
        if self.mapBitmap is None:
            return

        if event is None:
            dc = wx.ClientDC(self.map_pane)
        else:
            pdc = wx.AutoBufferedPaintDC(self.map_pane)
            try:
                dc = wx.GCDC(pdc)
            except:
                dc = pdc

        dc.BeginDrawing()

        # Draw background
        dc.DrawBitmap(self.mapBitmap, 0, 0)

        # Draw robot
        if self.robotPos is not None:
            [x,y] = map(lambda x: int(self.mapScale*x), self.robotPos) 
            dc.SetBrush(wx.Brush(wx.WHITE, wx.SOLID))
            dc.DrawCircle(x, y, 5)

        # Draw fiducials
        for fid_name, fid_pos in self.fiducialPositions.iteritems():
            [x,y] = map(lambda x: int(self.mapScale*x), fid_pos) 
            dc.SetBrush(wx.Brush(wx.BLACK, wx.SOLID))
            dc.DrawCircle(x, y, 5)

            # Draw label
            dc.SetTextForeground(wx.BLACK)
            dc.SetBackgroundMode(wx.TRANSPARENT)
            font = wx.Font(12, wx.FONTFAMILY_SWISS, wx.NORMAL, wx.NORMAL, False)
            dc.SetFont(font)
            
            textWidth, textHeight = dc.GetTextExtent(fid_name)
            
            textX = x + 8 # - textWidth/2
            textY = y - 0.5*textHeight
            dc.DrawText(fid_name, textX, textY)

#        if self.markerPos is not None:
#            [m,n] = map(lambda m: int(self.mapScale*m), self.markerPos) 
#            dc.SetBrush(wx.Brush(wx.RED))
#            dc.DrawCircle(m, n, 5)

        dc.EndDrawing()
        
        if event is not None:
            event.Skip()

# end of class GumboMainFrame

class BarebonesDialogueManager(object):
    def __init__(self, gui_window, executor, base_spec=None):
        """ take reference to execution context and gui_window
            optionally initialize with some base spec text """

        self.gui = gui_window
        self.executor = executor

        if base_spec is None:
            self.base_spec = []
        else:
            self.base_spec = base_spec.split("\n")

        self.spec = []

        # Initiate a specCompiler to hang around and give us immediate parser feedback
        self.compiler = SpecCompiler()
        self.compiler.proj = self.gui.proj

    def tell(self, message):
        """ take in a message from the user, return a response"""
        msg = message.lower().strip()
        if msg == "clear":
            self.spec = []
            return "Cleared the specification."
        elif msg == "go":
            # TODO: don't resynthesize if the specification hasn't changed?
            #       i.e. distinguish between resuming from pause, versus a new command

            # pause
            self.executor.pause()

            self.gui.appendLog("Please wait...", "System") 

            # trigger resynthesis
            success = self.executor.resynthesizeFromNewSpecification(self.getSpec())
            if success:
                # resume
                self.executor.resume()
                return "Doing as you asked."
            else:
                return "I'm sorry, I can't do that.\nPlease try something else."
        elif msg == "wait":
            self.executor.pause()
            return "Paused."
        elif msg == "status":
            if not self.executor.isRunning():
                return "Currently paused."

            curr_goal_num = self.executor.getCurrentGoalNumber()
            if curr_goal_num is None:
                return "I'm not doing anything right now."
            else:
                return "I'm currently pursuing goal #{}.".format(curr_goal_num)
        elif msg == "list":
            return "\n".join(self.spec)
        else:
            # Ask parser if this individual line is OK
            # FIXME: Because _writeLTLFile() is so monolithic, this will
            # clobber the `.ltl` file
            # FIXME: This may only work with SLURP
            self.compiler.proj.specText = message.strip()
            spec, tracebackTree, response = self.compiler._writeLTLFile()
            if spec is not None:
                self.spec.append(message.strip())
            return response[0]

    def getSpec(self):
        """ return the current specification as one big string """
        return "\n".join(self.base_spec + self.spec)

class GumboMainApp(wx.App):
    def OnInit(self):
        wx.InitAllImageHandlers()
        gumboMainFrame = GumboMainFrame(None, wx.ID_ANY, "")
        self.SetTopWindow(gumboMainFrame)
        gumboMainFrame.Show()
        return 1

# end of class GumboMainApp


if __name__ == "__main__":
    gettext.install("gumboMainApp") # replace with the appropriate catalog name

    gumboMainApp = GumboMainApp(0)
    gumboMainApp.MainLoop()
