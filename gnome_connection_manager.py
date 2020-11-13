#!/usr/bin/python3
# -*- coding: UTF-8 -*-

from __future__ import with_statement
import os
import operator
import sys
import base64
import time
import tempfile
import traceback
import re
import shlex
import cairo

try:
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('Vte', '2.91')
    from gi.repository import Gtk, Gdk, Vte, Pango, GObject, GdkPixbuf, GLib
except:
    print >> sys.stderr, "python3-gi required"
    sys.exit(1)

#check Terminal version
TERMINAL_V048 = 'spawn_async' in Vte.Terminal.__dict__

#Ver si expect esta instalado
try:
    e = os.system("expect >/dev/null 2>&1 -v")
except:
    e = -1
if e != 0:
    error = Gtk.MessageDialog (modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text='You must install expect')
    error.run()
    sys.exit (1)

#Gdk.threads_init()

from SimpleGladeApp import SimpleGladeApp
from SimpleGladeApp import bindtextdomain

import configparser
import pyAES
import urlregex

app_name = "Gnome Connection Manager"
app_version = "1.2.1"
app_web = "http://www.kuthulu.com/gcm"
app_fileversion = "1"

BASE_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))

SSH_BIN = 'ssh'
TEL_BIN = 'telnet'
SHELL   = os.environ["SHELL"]
DEFAULT_TERM_TYPE = 'xterm-256color'

SSH_COMMAND = BASE_PATH + "/ssh.expect"
try:
    USERHOME_DIR = os.getenv("HOME")
except:
    USERHOME_DIR = ""
if USERHOME_DIR is None or USERHOME_DIR == "":
    try:
        USERHOME_DIR = os.path.expanduser("~")
    except:
        USERHOME_DIR = ""

assert( (USERHOME_DIR is not None) and (USERHOME_DIR != "") ), \
    "FATAL: Could not determine home directory for the current user";

assert os.path.isdir(USERHOME_DIR), \
    "FATAL: Could not locate home directory '%s' for the current user" % (USERHOME_DIR);

CONFIG_DIR = USERHOME_DIR + "/.gcm"
CONFIG_FILE = CONFIG_DIR + "/gcm.conf"
KEY_FILE = CONFIG_DIR + "/.gcm.key"

if not os.path.exists(CONFIG_DIR):
    os.makedirs(CONFIG_DIR)

domain_name="gcm-lang"

#these colors are defined in vte sourcecode, but there is no way to read them (vte.cc 0.60.1, line 2371)
DEFAULT_BGCOLOR = "#000000"
DEFAULT_FGCOLOR = "#C0C0C0"

HSPLIT = 0
VSPLIT = 1

_COPY =      ["copy"]
_PASTE =     ["paste"]
_COPY_ALL =  ["copy_all"]
_SAVE =      ["save"]
_FIND =      ["find"]
_CLEAR =     ["reset"]
_FIND_NEXT = ["find_next"]
_FIND_BACK = ["find_back"]
_CONSOLE_PREV = ["console_previous"]
_CONSOLE_NEXT = ["console_next"]
_CONSOLE_1 = ["console_1"]
_CONSOLE_2 = ["console_2"]
_CONSOLE_3 = ["console_3"]
_CONSOLE_4 = ["console_4"]
_CONSOLE_5 = ["console_5"]
_CONSOLE_6 = ["console_6"]
_CONSOLE_7 = ["console_7"]
_CONSOLE_8 = ["console_8"]
_CONSOLE_9 = ["console_9"]
_CONSOLE_CLOSE = ["console_close"]
_CONSOLE_RECONNECT = ["console_reconnect"]
_CONNECT = ["connect"]
_NEW_LOCAL = ["new_local"]
_CLONE = ["clone"]

ICON_PATH = BASE_PATH + "/icon.png"

glade_dir = ""
locale_dir = BASE_PATH + "/lang"

bindtextdomain(domain_name, locale_dir)

groups={}
shortcuts={}

enc_passwd=''

#Variables de configuracion
class conf():
    WORD_SEPARATORS="-A-Za-z0-9,./?%&#:_=+@~"
    BUFFER_LINES=2000
    STARTUP_LOCAL=True
    LOG_LOCAL=False
    CONFIRM_ON_EXIT=True
    FONT_COLOR = ""
    BACK_COLOR = ""
    TRANSPARENCY = 0
    TERM = ""
    PASTE_ON_RIGHT_CLICK = 1
    CONFIRM_ON_CLOSE_TAB = 1
    CONFIRM_ON_CLOSE_TAB_MIDDLE = 1
    AUTO_CLOSE_TAB = 0
    COLLAPSED_FOLDERS = ""
    LEFT_PANEL_WIDTH = 100
    CHECK_UPDATES=True
    WINDOW_WIDTH = -1
    WINDOW_HEIGHT = -1
    FONT = ""
    HIDE_DONATE = False
    AUTO_COPY_SELECTION = 0
    LOG_PATH = CONFIG_DIR + "/logs"
    SHOW_TOOLBAR = True
    SHOW_PANEL = True
    VERSION = 0
    UPDATE_TITLE = 0
    APP_TITLE = app_name

def msgbox(text, parent=None):
    msgBox = Gtk.MessageDialog(parent=parent, modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=text)
    msgBox.set_icon_from_file(ICON_PATH)
    msgBox.run()    
    msgBox.destroy()

def msgconfirm(text):
    msgBox = Gtk.MessageDialog(parent=wMain.window, modal=True, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.OK_CANCEL, text=text)
    msgBox.set_icon_from_file(ICON_PATH)
    response = msgBox.run()    
    msgBox.destroy()
    return response


def inputbox(title, text, default='', password=False):
    msgBox = EntryDialog(title, text, default, mask=password)
    msgBox.set_icon_from_file(ICON_PATH)
    if msgBox.run() == Gtk.ResponseType.OK:
        response = msgBox.value
    else:
        response = None
    msgBox.destroy()
    return response

def show_font_dialog(parent, title, button):
    if not hasattr(parent, 'dlgFont'):
        parent.dlgFont = None
        
    if parent.dlgFont == None:
        parent.dlgFont = Gtk.FontSelectionDialog(title)
    fontsel = parent.dlgFont.get_font_selection()
    fontsel.set_font_name(button.selected_font.to_string())    

    response = parent.dlgFont.run()

    if response == Gtk.ResponseType.OK:        
        button.selected_font = Pango.FontDescription(fontsel.get_font_name())        
        button.set_label(button.selected_font.to_string())
        button.get_child().modify_font(button.selected_font)
    parent.dlgFont.hide()
    
def show_open_dialog(parent, title, action):        
    dlg = Gtk.FileChooserDialog(title=title, parent=parent, action=action)
    dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
    
    dlg.add_button(Gtk.STOCK_SAVE if action==Gtk.FileChooserAction.SAVE else Gtk.STOCK_OPEN, Gtk.ResponseType.OK)        
    dlg.set_do_overwrite_confirmation(True)        
    if not hasattr(parent,'lastPath'):
        parent.lastPath = USERHOME_DIR
    dlg.set_current_folder( parent.lastPath )
    
    if dlg.run() == Gtk.ResponseType.OK:
        filename = dlg.get_filename()
        parent.lastPath = os.path.dirname(filename)
    else:
        filename = None
    dlg.destroy()
    return filename
            
def parse_color_rgba(spec):
    rgba = Gdk.RGBA()
    b = rgba.parse(spec)        
    return rgba

def parse_color(spec):    
    return parse_color_rgba(spec).to_color()

def color_to_hex(rgba, diff=0):
    return "#%x%x%x" % (int(rgba.red*255+diff),int(rgba.green*255+diff),int(rgba.blue*255+diff))

        
def get_key_name(event):
    name = ""
    if event.state & Gdk.ModifierType.CONTROL_MASK:
        name = name + "CTRL+"
    if event.state & Gdk.ModifierType.SHIFT_MASK:
        name = name + "SHIFT+"
    if event.state & Gdk.ModifierType.MOD1_MASK:
        name = name + "ALT+"
    if event.state & Gdk.ModifierType.SUPER_MASK:
        name = name + "SUPER+"
    return name + Gdk.keyval_name(event.keyval).upper()
     
def get_username():
    return os.getenv('USER') or os.getenv('LOGNAME') or os.getenv('USERNAME')

def get_password():
    return get_username() + enc_passwd
    
def load_encryption_key():
    global enc_passwd
    try:
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE) as f:
                enc_passwd = f.read()
        else:
            enc_passwd = ''
    except:
        msgbox("Error trying to open key_file")
        enc_passwd = ''

def initialise_encyption_key():
    global enc_passwd
    import random
    x = int(str(random.random())[2:])
    y = int(str(random.random())[2:])
    enc_passwd = "%x" % (x*y)
    try:
        with os.fdopen(os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT, 0o600), 'w') as f:
            f.write(enc_passwd)
    except:
        msgbox("Error initialising key_file")

## funciones para encryptar passwords - no son muy seguras, pero impiden que los pass se guarden en texto plano
def xor(pw, str1):
    c = 0
    liste = []
    for k in xrange(len(str1)):
        if c > len(pw)-1:
            c = 0
        fi = ord(pw[c])
        c += 1
        se = ord(str1[k])
        fin = operator.xor(fi, se)
        liste += [chr(fin)]
    return liste
        
def encrypt_old(passw, string):
    try:
        ret = xor(passw, string)    
        s = base64.b64encode("".join(ret))
    except:
        s = ""
    return s
 
def decrypt_old(passw, string):
    try:
        ret = xor(passw, base64.b64decode(string))
        s = "".join(ret)
    except:
        s = ""
    return s
    
def encrypt(passw, string):
    try:
        s = pyAES.encrypt(string, passw)
    except:
        traceback.print_exc()
        s = ""
    return s
 
def decrypt(passw, string):
    try:
        s = decrypt_old(passw, string) if conf.VERSION == 0 else pyAES.decrypt(string, passw)
    except:
        traceback.print_exc()
        s = ""
    return s

def vte_feed(terminal, data):
    if TERMINAL_V048 or (Vte.MAJOR_VERSION, Vte.MINOR_VERSION) >= (0, 42):
        try:
            terminal.feed_child(data.encode('utf-8'))
        except TypeError as e:
            # https://bugs.launchpad.net/ubuntu/+source/ubuntu-release-upgrader/+bug/1780501
            # The doc does not say clearly at which version the feed_child* function has lost # the "len" parameter :(
            terminal.feed_child(data, len(data))
    else:
        terminal.feed_child(data, len(data))

def vte_run(terminal, command, arg=None):
    term_type = terminal.host.term if hasattr(terminal, 'host') and terminal.host.term else conf.TERM or os.getenv("TERM") or DEFAULT_TERM_TYPE
    envv = [ 'PATH=%s' % os.getenv("PATH"), 'TERM=%s' % term_type ]
    args = []
    args.append(command)
    if arg:
        args += arg
    flag_spawn = GLib.SpawnFlags.DEFAULT if command == SHELL else GLib.SpawnFlags.FILE_AND_ARGV_ZERO
    if TERMINAL_V048:
        terminal.spawn_async(Vte.PtyFlags.DEFAULT,
                           os.getenv("HOME"),
                           args,
                           envv,
                           flag_spawn | GLib.SpawnFlags.DO_NOT_REAP_CHILD | GLib.SpawnFlags.SEARCH_PATH,
                           None,
                           None,
                           -1,
                           None,
                           None)
    else:
        terminal.spawn_sync(Vte.PtyFlags.DEFAULT,
                           os.getenv("HOME"),
                           args,
                           envv,
                           flag_spawn | GLib.SpawnFlags.DO_NOT_REAP_CHILD | GLib.SpawnFlags.SEARCH_PATH,
                           None,
                           None,
                           None)

class Wmain(SimpleGladeApp):

    def __init__(self, path="gnome-connection-manager.glade",
                 root="wMain",
                 domain=domain_name, **kwargs):
        path = os.path.join(glade_dir, path)
        SimpleGladeApp.__init__(self, path, root, domain, **kwargs)

        global wMain
        wMain = self                
        
        load_encryption_key()
        
        self.initLeftPane()     

        self.createMenu()
        self.window = self.get_widget("wMain")

        if conf.VERSION == 0:
            initialise_encyption_key()
        
        settings = Gtk.Settings.get_default()
        settings.props.gtk_menu_bar_accel = None

        self.enable_window_transparency(self.window)
        self.window.connect("style-updated", self.enable_window_transparency)

        self.update_visual()
        self.get_widget("wMain").get_screen().connect('composited-changed', self.update_visual)

        if conf.WINDOW_WIDTH != -1 and conf.WINDOW_HEIGHT != -1:
            self.get_widget("wMain").resize(conf.WINDOW_WIDTH, conf.WINDOW_HEIGHT)
        else:
            self.get_widget("wMain").maximize()        
        self.get_widget("wMain").show()
        #Just added children in glade to eliminate GTK warning, remove all children
        for x in self.nbConsole.get_children():
            self.nbConsole.remove(x)
        self.nbConsole.set_scrollable(True)
        self.nbConsole.set_group_name("11")
        self.nbConsole.connect('page_removed', self.on_page_removed)        
        self.nbConsole.connect("page-added", self.on_page_added)
        self.nbConsole.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.nbConsole.connect("scroll-event", self.on_tab_scroll)
                
        self.hpMain.previous_position = 150
        
        if conf.LEFT_PANEL_WIDTH!=0:
            self.set_panel_visible(conf.SHOW_PANEL)
        self.set_toolbar_visible(conf.SHOW_TOOLBAR)
        
        #a veces no se posiciona correctamente con 400 ms, asi que se repite el llamado 
        GLib.timeout_add(400, lambda : self.hpMain.set_position(conf.LEFT_PANEL_WIDTH))
        GLib.timeout_add(900, lambda : self.hpMain.set_position(conf.LEFT_PANEL_WIDTH))

        if conf.HIDE_DONATE:
            self.get_widget("btnDonate").hide()
        
        if conf.CHECK_UPDATES:
            GLib.timeout_add(2000, lambda: self.check_updates())
        
        #Por cada parametro de la linea de comandos buscar el host y agregar un tab
        for arg in sys.argv[1:]:
            i = arg.rfind("/")
            if i!=-1:
                group = arg[:i]
                name = arg[i+1:]                 
                if group!='' and name!='' and group in groups:
                    for h in groups[group]:                                
                        if h.name==name:
                            self.addTab(self.nbConsole, h)
                            break                
        
        self.get_widget('txtSearch').override_color(Gtk.StateFlags.NORMAL, parse_color_rgba('darkgray'))
        
        if conf.STARTUP_LOCAL:
            self.addTab(self.nbConsole,'local')

    def update_visual(self):
        window = self.get_widget("wMain")
        screen = window.get_screen()
        visual = screen.get_rgba_visual()
        if visual and screen.is_composited():
            # NOTE: We should re-realize window when update window visual
            # Otherwise it may failed, when the gcm is started without compositor
            window.unrealize()
            window.set_visual(visual)
            window.transparency = True
            window.realize()
            if window.get_property('visible'):
                window.hide()
                window.show()
        else:
            sys.stderr.write('System doesn\'t support transparency')
            window.transparency = False
            window.set_visual(screen.get_system_visual())


    def enable_window_transparency(self, window):
        #hack to allow transparent widgets inside a opaque window
        #the key is to set the alpha channel of the window's background color to 0.9999, in that way the window is opaque but still allows transparent children

        #remove previously addded css to get the background color from the current gtk theme
        if hasattr(window, "style_provider") and window.style_provider:
            Gtk.StyleContext.remove_provider_for_screen(
                Gdk.Screen.get_default(),
                window.style_provider
            )

        #get window background color
        context = window.get_style_context()
        color = context.get_background_color(Gtk.StateFlags.NORMAL)

        #set the background color to the same as the gtk theme, but with alpha 0.99999 (it looks opaque but allows to have transparent widgets)
        CSS = b"""
        window.background {
            background-color: rgba(%d, %d, %d, %f);
        }
        """ % (color.red*255, color.green*255, color.blue*255, 0.999999)

        window.style_provider = Gtk.CssProvider()
        window.style_provider.load_from_data(CSS)

        context.add_provider_for_screen(
            window.get_screen(),
            window.style_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    #-- Wmain.new {
    def new(self):        
        self.hpMain = self.get_widget("hpMain")
        self.nbConsole = self.get_widget("nbConsole")
        self.treeServers = self.get_widget("treeServers")
        self.menuServers = self.get_widget("menuServers")
        self.menuCustomCommands = self.get_widget("menuCustomCommands")
        self.current = None
        self.count = 0
        self.row_activated = False
    #-- Wmain.new }

    #-- Wmain custom methods {           
    #   Write your own methods here
        
    def check_updates(self):
        checker = CheckUpdates(self)        
        checker.start()
            
    def on_terminal_click(self, widget, event, *args):      
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            if conf.PASTE_ON_RIGHT_CLICK:
                widget.paste_clipboard()
            else:
                self.popupMenu.mnuCopy.set_sensitive(widget.get_has_selection()) 
                self.popupMenu.mnuLog.set_active( hasattr(widget, "log_handler_id") and widget.log_handler_id != 0 )
                self.popupMenu.terminal = widget
                self.popupMenu.popup( None, None, None, None, event.button, event.time)
            return True
    
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1 and event.get_state() &  Gdk.ModifierType.CONTROL_MASK:
            url, tag = widget.match_check_event(event)
            if tag == widget.tag_url:
                url = "http://%s" % url
            elif tag == widget.tag_email and not url.startswith("mailto:"):
                url = "mailto://%s" % url
            url = url or widget.hyperlink_check_event(event)
            if url:
                Gtk.show_uri(Gdk.Screen.get_default(), url, Gtk.get_current_event_time())

        #terminal doesnt emmit the "focus" signal when there is more than one visible on the screen, so force the focus
        nb = widget.get_parent().get_parent()
        self.on_tab_focus(nb, nb.get_nth_page(nb.get_current_page()), nb.get_current_page())

    def on_terminal_keypress(self, widget, event, *args):
        #if shortcuts.has_key(get_key_name(event)):
        if get_key_name(event) in shortcuts:
            cmd = shortcuts[get_key_name(event)]
            if type(cmd) == list:
                #comandos predefinidos
                if cmd == _COPY:
                    self.terminal_copy(widget)
                elif cmd == _PASTE:
                    self.terminal_paste(widget)
                elif cmd == _COPY_ALL:
                    self.terminal_copy_all(widget)
                elif cmd == _SAVE:
                    self.show_save_buffer(widget)
                elif cmd == _FIND:
                    self.get_widget('txtSearch').select_region(0, -1)
                    self.get_widget('txtSearch').grab_focus()
                elif cmd == _FIND_NEXT:
                    if hasattr(self, 'search'):
                        self.find_word()
                elif cmd == _CLEAR:
                   widget.reset(True, True)
                elif cmd == _FIND_BACK:
                    if hasattr(self, 'search'):
                        self.find_word(backwards=True)
                elif cmd == _CLONE:
                    term = widget
                    ntbk = widget.get_parent().get_parent()
                    tab = ntbk.get_tab_label(term.get_parent())
                    if not hasattr(term, "host"):
                        self.addTab(ntbk, tab.get_text())
                    else:
                        host = term.host.clone()
                        host.name = tab.get_text()
                        host.log = hasattr(term, "log_handler_id") and term.log_handler_id != 0
                        self.addTab(ntbk, host)
                elif cmd == _CONSOLE_PREV:
                    ntbk = widget.get_parent().get_parent()
                    if ntbk.get_current_page() == 0:
                        ntbk.set_current_page(len(ntbk) - 1)
                    else:
                        ntbk.prev_page()
                elif cmd == _CONSOLE_NEXT:
                    ntbk = widget.get_parent().get_parent()
                    if ntbk.get_current_page() == len(ntbk) - 1:
                        ntbk.set_current_page(0)
                    else:
                        ntbk.next_page()
                elif cmd == _CONSOLE_CLOSE:
                    wid = widget.get_parent()                    
                    page = widget.get_parent().get_parent().page_num(wid)                    
                    if page != -1:
                        widget.get_parent().get_parent().remove_page(page)
                        wid.destroy()
                elif cmd == _CONSOLE_RECONNECT:                    
                    if not hasattr(widget, "command"):
                        #widget.fork_command(SHELL)
                        vte_run(widget, SHELL)
                    else:
                        #widget.fork_command(widget.command[0], widget.command[1])
                        vte_run(widget, widget.command[0], widget.command[1])
                        while Gtk.events_pending():
                            Gtk.main_iteration()                                
                            
                        #esperar 2 seg antes de enviar el pass para dar tiempo a que se levante expect y prevenir que se muestre el pass
                        if widget.command[2]!=None and widget.command[2]!='':
                            GLib.timeout_add(2000, self.send_data, widget, widget.command[2])                    
                    widget.get_parent().get_parent().get_tab_label(widget.get_parent()).mark_tab_as_active()
                    return True
                elif cmd == _CONNECT:
                    self.on_btnConnect_clicked(None)
                elif cmd[0][0:8] == "console_":
                    page = int(cmd[0][8:]) - 1                   
                    widget.get_parent().get_parent().set_current_page(page)             
                elif cmd == _NEW_LOCAL:
                    self.on_btnLocal_clicked(None)
            else:
                #comandos del usuario
                vte_feed(widget, cmd)
                
            return True
        return False

    def on_terminal_selection(self, widget, *args):
        if conf.AUTO_COPY_SELECTION:
            self.terminal_copy(widget)
        return True
        
    def find_word(self, backwards=False):
        if not self.search:
            return

        if (self.search['pcre2']):
            if backwards:
                self.search['terminal'].search_find_previous()
            else:
                self.search['terminal'].search_find_next()
            return

        pos=-1        
        if backwards:
            lst = list(range(0, self.search['index']))
            lst.reverse()
            lst.extend(reversed(range(self.search['index'], len(self.search['lines']))))
        else:
            lst = list(range(self.search['index'], len(self.search['lines'])))
            lst.extend(range(0, self.search['index']))
        for i in lst:
            pos = self.search['lines'][i].find(self.search['word'])
            if pos != -1:                
                self.search['index'] = i if backwards else i + 1
                #print('found at line %d column %d, index=%d, line: %s' % (i, pos, self.search['index'], self.search['lines'][i]))                
                GLib.timeout_add(0, lambda: self.search['terminal'].get_vadjustment().set_value(i))
                #self.search['terminal'].get_vadjustment().set_value(i)
                self.search['terminal'].queue_draw()
                break
        if pos==-1:
            self.search['index'] = len(self.search['lines']) if backwards else 0
    
    
    def init_search(self):
        if hasattr(self, 'search') and self.search and self.get_widget('txtSearch').get_text() == self.search['word'] and self.current == self.search['terminal']:                        
            return  True
            
        terminal = self.find_active_terminal(self.hpMain)
        if terminal == None:
            terminal = self.current
        else:
            self.current = terminal
        if terminal==None:            
            return False                           

        self.search = {}
        text = self.get_widget('txtSearch').get_text()
        if text == '' or text == _('buscar...'):
            terminal.search_set_regex(None, 0)
            terminal.match_remove_all()
            return True

        self.search['terminal'] = terminal
        self.search['word'] = text       

        r = re.escape(text)                
        try:
            new_reg = Vte.Regex.new_for_search(r, len(r), 0)            
            new_reg_m = Vte.Regex.new_for_match(r, len(r), 0)     
            terminal.search_set_regex(new_reg, 0)
            terminal.search_set_wrap_around(True)
            terminal.match_add_regex(new_reg_m, 0)
            self.search['pcre2'] = True
            return True
        except Exception as e:
            print(e, "Using custom search instead")   
            self.search['pcre2'] = False
            #no hay soporte para pcre2, usar busqueda artesanal
            
                            
        cols = terminal.get_column_count()
        lines,b = terminal.get_text_range(0, 0, terminal.get_property('scrollback-lines'), cols, None, None )
        wrapped = []
        for x in lines.splitlines():
            if len(x)==0:
                wrapped.append(x)
            else:
                wrapped += self.chunkstring(x, cols)
        self.search['lines'] = wrapped
        self.search['index'] = len(self.search['lines'])        
        return True
    
    def chunkstring(self, string, length):
        return (string[0+i:length+i] for i in range(0, len(string), length))

    def on_popupmenu(self, widget, item, *args):        
        if item == 'V': #PASTE
            self.terminal_paste(self.popupMenu.terminal)
            return True
        elif item == 'C': #COPY
            self.terminal_copy(self.popupMenu.terminal)
            return True
        elif item == 'CV': #COPY and PASTE
            self.terminal_copy_paste(self.popupMenu.terminal)
            return True            
        elif item == 'A': #SELECT ALL
            self.terminal_select_all(self.popupMenu.terminal)
            return True
        elif item == 'CA': #COPY ALL
            self.terminal_copy_all(self.popupMenu.terminal)
            return True
        elif item == 'X': #CLOSE CONSOLE
            widget = self.popupMenu.terminal.get_parent()
            notebook = widget.get_parent()
            page=notebook.page_num(widget)         
            notebook.remove_page(page)
            return True
        elif item == 'CP': #CUSTOM COMMANDS
            vte_feed(self.popupMenu.terminal, args[0])
        elif item == 'S': #SAVE BUFFER
            self.show_save_buffer(self.popupMenu.terminal)
            return True
        elif item == 'H': #COPY HOST ADDRESS TO CLIPBOARD
            if self.treeServers.get_selection().get_selected()[1]!=None and not self.treeModel.iter_has_child(self.treeServers.get_selection().get_selected()[1]):
                host = self.treeModel.get_value(self.treeServers.get_selection().get_selected()[1],1)                
                cb = Gtk.Clipboard.get_default(Gdk.Display.get_default())
                cb.set_text(host.host, len(host.host))
                cb.store()
            return True
        elif item == 'D': #DUPLICATE HOST
            if self.treeServers.get_selection().get_selected()[1]!=None and not self.treeModel.iter_has_child(self.treeServers.get_selection().get_selected()[1]):                
                selected = self.treeServers.get_selection().get_selected()[1]            
                group = self.get_group(selected)
                host = self.treeModel.get_value(selected, 1)
                newname = '%s (copy)' % (host.name)
                newhost = host.clone()
                for h in groups[group]:
                    if h.name == newname:
                        newname = '%s (copy)' % (newname)
                newhost.name = newname
                groups[group].append( newhost )
                self.updateTree()
                self.writeConfig()
            return True            
        elif item == 'R': #RENAME TAB
            text = inputbox(_('Renombrar consola'), _('Ingrese nuevo nombre'), self.popupMenuTab.label.get_text().strip())
            if text != None and text != '':
                self.popupMenuTab.label.set_text("  %s  " % (text))
                nb = self.popupMenuTab.label.get_parent().get_parent().get_parent()
                nb.emit('switch-page', nb.get_nth_page(nb.get_current_page()), nb.get_current_page())
            return True
        elif item == 'RS' or item == 'RS2': #RESET CONSOLE              
            if (item == 'RS'):
                tab = self.popupMenuTab.label.get_parent().get_parent()
                term = tab.widget_.get_child()
            else:
                term = self.popupMenu.terminal
            term.reset(True, False)
            return True
        elif item == 'RC' or item == 'RC2': #RESET AND CLEAR CONSOLE
            if (item == 'RC'):
                tab = self.popupMenuTab.label.get_parent().get_parent()
                term = tab.widget_.get_child()
            else:
                term = self.popupMenu.terminal
            term.reset(True, True)
            return True
        elif item == 'RO': #REOPEN SESION
            tab = self.popupMenuTab.label.get_parent().get_parent()
            term = tab.widget_.get_child()
            if not hasattr(term, "command"):
                #term.fork_command(SHELL)
                vte_run(term, SHELL)
            else:
                #term.fork_command(term.command[0], term.command[1])
                vte_run(term, term.command[0], term.command[1])
                while Gtk.events_pending():
                    Gtk.main_iteration()                                
                    
                #esperar 2 seg antes de enviar el pass para dar tiempo a que se levante expect y prevenir que se muestre el pass
                if term.command[2]!=None and term.command[2]!='':
                    GLib.timeout_add(2000, self.send_data, term, term.command[2])
            tab.mark_tab_as_active()
            return True
        elif item == 'CC' or item == 'CC2': #CLONE CONSOLE
            if item == 'CC':
                tab = self.popupMenuTab.label.get_parent().get_parent()
                term = tab.widget_.get_child()
                ntbk = tab.get_parent()
            else:
                term = self.popupMenu.terminal
                ntbk = term.get_parent().get_parent() 
                tab = ntbk.get_tab_label(term.get_parent())               
            if not hasattr(term, "host"):
                self.addTab(ntbk, tab.get_text())
            else:
                host = term.host.clone()
                host.name = tab.get_text()
                host.log = hasattr(term, "log_handler_id") and term.log_handler_id != 0
                self.addTab(ntbk, host)
            return True
        elif item == 'L' or item == 'L2': #ENABLE/DISABLE LOG
            if item == 'L':
                tab = self.popupMenuTab.label.get_parent().get_parent()
                term = tab.widget_.get_child()
            else:
                term = self.popupMenu.terminal
            if not self.set_terminal_logger(term, widget.get_active()):
                widget.set_active(False)
            return True
                
    def createMenu(self):
        self.popupMenu = Gtk.Menu()
        self.popupMenu.mnuCopy = menuItem = Gtk.ImageMenuItem(label=_("Copiar"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_COPY, Gtk.IconSize.MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'C')
        menuItem.show()
        
        self.popupMenu.mnuPaste = menuItem = Gtk.ImageMenuItem(label=_("Pegar"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_PASTE, Gtk.IconSize.MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'V')
        menuItem.show()
        
        self.popupMenu.mnuCopyPaste = menuItem = Gtk.ImageMenuItem(label=_("Copiar y Pegar"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_INDEX, Gtk.IconSize.MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'CV')
        menuItem.show()
        
        self.popupMenu.mnuSelect = menuItem = Gtk.ImageMenuItem(label=_("Seleccionar todo"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_SELECT_ALL, Gtk.IconSize.MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'A')
        menuItem.show()
        
        self.popupMenu.mnuCopyAll = menuItem = Gtk.ImageMenuItem(label=_("Copiar todo"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_SELECT_ALL, Gtk.IconSize.MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'CA')
        menuItem.show()
        
        self.popupMenu.mnuSelect = menuItem = Gtk.ImageMenuItem(label=_("Guardar buffer en archivo"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_SAVE, Gtk.IconSize.MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'S')
        menuItem.show()
        
        menuItem = Gtk.MenuItem()
        self.popupMenu.append(menuItem)
        menuItem.show()
        
        self.popupMenu.mnuReset = menuItem = Gtk.ImageMenuItem(label=_("Reiniciar consola"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_NEW, Gtk.IconSize.MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'RS2')
        menuItem.show()
        
        self.popupMenu.mnuClear = menuItem = Gtk.ImageMenuItem(label=_("Reiniciar y Limpiar consola"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_CLEAR, Gtk.IconSize.MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'RC2')
        menuItem.show()
        
        self.popupMenu.mnuClone = menuItem = Gtk.ImageMenuItem(label=_("Clonar consola"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_COPY, Gtk.IconSize.MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'CC2')
        menuItem.show()

        self.popupMenu.mnuLog = menuItem = Gtk.CheckMenuItem(label=_("Habilitar log"))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'L2')
        menuItem.show()
        
        self.popupMenu.mnuClose = menuItem = Gtk.ImageMenuItem(label=_("Cerrar consola"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_CLOSE, Gtk.IconSize.MENU))
        self.popupMenu.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'X')
        menuItem.show()
        
        menuItem = Gtk.MenuItem()
        self.popupMenu.append(menuItem)
        menuItem.show()
        
        #Menu de comandos personalizados
        self.popupMenu.mnuCommands = Gtk.Menu()
        
        self.popupMenu.mnuCmds = menuItem = Gtk.ImageMenuItem(label=_("Comandos personalizados"))
        menuItem.set_submenu(self.popupMenu.mnuCommands)
        self.popupMenu.append(menuItem)
        menuItem.show()
        self.populateCommandsMenu()
                
        #Menu contextual para panel de servidores
        self.popupMenuFolder = Gtk.Menu()
        
        self.popupMenuFolder.mnuConnect = menuItem = Gtk.ImageMenuItem(label=_("Conectar"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_EXECUTE, Gtk.IconSize.MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_btnConnect_clicked)
        menuItem.show()

        self.popupMenuFolder.mnuCopyAddress = menuItem = Gtk.ImageMenuItem(label=_("Copiar Direccion"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_COPY, Gtk.IconSize.MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'H')
        menuItem.show()
        
        self.popupMenuFolder.mnuAdd = menuItem = Gtk.ImageMenuItem(label=_("Agregar Host"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_ADD, Gtk.IconSize.MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_btnAdd_clicked)
        menuItem.show()
        
        self.popupMenuFolder.mnuEdit = menuItem = Gtk.ImageMenuItem(label=_("Editar"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_EDIT, Gtk.IconSize.MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_bntEdit_clicked)
        menuItem.show()
        
        self.popupMenuFolder.mnuDel = menuItem = Gtk.ImageMenuItem(label=_("Eliminar"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_DELETE, Gtk.IconSize.MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_btnDel_clicked)
        menuItem.show()
        
        self.popupMenuFolder.mnuDup = menuItem = Gtk.ImageMenuItem(label=_("Duplicar Host"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_DND_MULTIPLE, Gtk.IconSize.MENU))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'D')
        menuItem.show()
        
        menuItem = Gtk.SeparatorMenuItem()
        self.popupMenuFolder.append(menuItem)
        menuItem.show()
        
        self.popupMenuFolder.mnuExpand = menuItem = Gtk.ImageMenuItem(label=_("Expandir todo"))        
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", lambda *args: self.treeServers.expand_all())
        menuItem.show()
        
        self.popupMenuFolder.mnuCollapse = menuItem = Gtk.ImageMenuItem(label=_("Contraer todo"))
        self.popupMenuFolder.append(menuItem)
        menuItem.connect("activate", lambda *args: self.treeServers.collapse_all())
        menuItem.show()
        
        
        #Menu contextual para tabs
        self.popupMenuTab = Gtk.Menu()
        
        self.popupMenuTab.mnuRename = menuItem = Gtk.ImageMenuItem(label=_("Renombrar consola"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_EDIT, Gtk.IconSize.MENU))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'R')
        menuItem.show()
        
        self.popupMenuTab.mnuReset = menuItem = Gtk.ImageMenuItem(label=_("Reiniciar consola"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_NEW, Gtk.IconSize.MENU))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'RS')
        menuItem.show()
        
        self.popupMenuTab.mnuClear = menuItem = Gtk.ImageMenuItem(label=_("Reiniciar y Limpiar consola"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_CLEAR, Gtk.IconSize.MENU))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'RC')
        menuItem.show()
        
        self.popupMenuTab.mnuReopen = menuItem = Gtk.ImageMenuItem(label=_("Reconectar al host"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_CONNECT, Gtk.IconSize.MENU))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'RO')                
        #menuItem.show()
        
        self.popupMenuTab.mnuClone = menuItem = Gtk.ImageMenuItem(label=_("Clonar consola"))
        menuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_COPY, Gtk.IconSize.MENU))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'CC')
        menuItem.show()

        self.popupMenuTab.mnuLog = menuItem = Gtk.CheckMenuItem(label=_("Habilitar log"))
        self.popupMenuTab.append(menuItem)
        menuItem.connect("activate", self.on_popupmenu, 'L')
        menuItem.show()
        
    def createMenuItem(self, shortcut, label):
        menuItem = Gtk.MenuItem('')
        text = "[%s] %s" % (shortcut, label)
        attrs = Pango.parse_markup("<span foreground='blue'  size='x-small'>[%s]</span> %s" % (GLib.markup_escape_text(shortcut, -1), GLib.markup_escape_text(label, -1)), -1, "0")
        menuItem.get_child().set_attributes(attrs[1])
        menuItem.get_child().set_label(text)
        menuItem.show()
        return menuItem
                
    def populateCommandsMenu(self):
        self.popupMenu.mnuCommands.foreach(lambda x: self.popupMenu.mnuCommands.remove(x))
        self.menuCustomCommands.foreach(lambda x: self.menuCustomCommands.remove(x))
        for x in shortcuts:
            if type(shortcuts[x]) != list:
                menuItem = self.createMenuItem(x, shortcuts[x][0:30])
                self.popupMenu.mnuCommands.append(menuItem)
                menuItem.connect("activate", self.on_popupmenu, 'CP', shortcuts[x])
                
                menuItem = self.createMenuItem(x, shortcuts[x][0:30])
                self.menuCustomCommands.append(menuItem)
                menuItem.connect("activate", self.on_menuCustomCommands_activate, shortcuts[x])
                
    def on_menuCustomCommands_activate(self, widget, command):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            vte_feed(terminal, command)
    
    def terminal_copy(self, terminal):
        terminal.copy_clipboard_format(Vte.Format.TEXT)

    def terminal_paste(self, terminal):
        terminal.paste_clipboard()
    
    def terminal_copy_paste(self, terminal):
        terminal.copy_clipboard_format(Vte.Format.TEXT)
        terminal.paste_clipboard()
          
    def terminal_select_all(self, terminal):
        terminal.select_all()

    def terminal_copy_all(self, terminal):
        terminal.select_all()
        terminal.copy_clipboard_format(Vte.Format.TEXT)
        terminal.select_none()
                    
    def on_menuCopy_activate(self, widget):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            self.terminal_copy(terminal)
    
    def on_menuPaste_activate(self, widget):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            self.terminal_paste(terminal)
        
    def on_menuCopyPaste_activate(self, widget):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            self.terminal_copy_paste(terminal)
            
    def on_menuSelectAll_activate(self, widget):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            self.terminal_select_all(terminal)
            
    def on_menuCopyAll_activate(self, widget):
        terminal = self.find_active_terminal(self.hpMain)
        if terminal:
            self.terminal_copy_all(terminal)
    
    def on_menuSettings_activate(self, widget):
        wConfig = Wconfig()

    def on_contents_changed(self, terminal):
        col,row = terminal.get_cursor_position()        
        if terminal.last_logged_row != row:
            text,b = terminal.get_text_range(terminal.last_logged_row, terminal.last_logged_col, row, col, None, None)
            terminal.last_logged_row = row  
            terminal.last_logged_col = col            
            terminal.log.write(text[:-1])

    def set_terminal_logger(self, terminal, enable_logging=True):        
        if enable_logging:
            terminal.last_logged_col, terminal.last_logged_row = terminal.get_cursor_position()
            if hasattr(terminal, "log_handler_id"):
                if terminal.log_handler_id == 0:
                    terminal.log_handler_id = terminal.connect('contents-changed', self.on_contents_changed)
                return True
            terminal.log_handler_id = terminal.connect('contents-changed', self.on_contents_changed)
            p = terminal.get_parent()        
            title = p.get_parent().get_tab_label(p).get_text().strip()
            LOG_PATH = os.path.expanduser(conf.LOG_PATH)
            prefix = "%s/%s-%s" % (LOG_PATH, title, time.strftime("%Y%m%d"))
            if not os.path.exists(LOG_PATH):
                os.makedirs(LOG_PATH)
            filename = ''
            for i in range(1,1000):
                if not os.path.exists("%s-%03i.log" % (prefix,i)):
                    filename = "%s-%03i.log" % (prefix,i)
                    break
            if filename == '':
                # End up appending to the latest log file...
                filename = "%s-%03i.log" % (prefix,i)
            filename == "%s-%03i.log" % (prefix,1)
            try:
                prepend = ''
                if os.path.exists(filename):
                    msgbox("%s\n%s" % (_("Anexar el archivo de log existente"), filename))
                    prepend = '\n\n===== %s =====\n\n' %(_("Fin del registro de sesión anterior"))
                terminal.log = open(filename, 'a', 1)
                terminal.log.write("%sSession '%s' opened at %s\n%s\n" % (prepend, title, time.strftime("%Y-%m-%d %H:%M:%S"), "-"*80))
            except Exception as e:
                print(e)
                msgbox("%s\n%s" % (_("No se puede abrir el archivo de log para escritura"), filename))
                terminal.disconnect(terminal.log_handler_id)
                del terminal.log_handler_id
                return False
        else:
            if hasattr(terminal, "log_handler_id") and terminal.log_handler_id != 0:
                terminal.disconnect(terminal.log_handler_id)
                terminal.log_handler_id = 0
        return True

    def registerUrlRegexes(self, terminal):
        terminal.tag_direct = self.registerUrlRegex(terminal, urlregex.DIRECT)
        terminal.tag_url = self.registerUrlRegex(terminal, urlregex.URL)
        terminal.tag_email = self.registerUrlRegex(terminal, urlregex.EMAIL)

    def registerUrlRegex(self, terminal, regex):
        try:
            new_reg_m = Vte.Regex.new_for_match(regex, len(regex), urlregex.PCRE2_FLAGS)
            tag = terminal.match_add_regex(new_reg_m, 0)
            terminal.match_set_cursor_name(tag, "pointer")
            return tag
        except Exception as e:
            pass

    def addTab(self, notebook, host):
        try:
            v = Vte.Terminal()
            v.set_word_char_exceptions(conf.WORD_SEPARATORS)
            v.set_scrollback_lines(conf.BUFFER_LINES)
            if (Vte.MAJOR_VERSION, Vte.MINOR_VERSION) >= (0, 50): 
                v.set_allow_hyperlink(True)
            self.registerUrlRegexes(v)
            
            if isinstance(host, str):
                host = Host('', host)
                # Note: log enablement defaults to host.log except for 'local'
                # sessions that do not have a saved session to seed the host
                # configuration, but rather use a global GCM config toggle
                if host.name == 'local':
                    #print ("D: Local session logging set to: %s\n" % (conf.LOG_LOCAL))
                    host.log = conf.LOG_LOCAL
            
            fcolor = host.font_color
            bcolor = host.back_color
            if fcolor == '' or fcolor == None or bcolor == '' or bcolor == None:
                fcolor = conf.FONT_COLOR
                bcolor = conf.BACK_COLOR

            palette_components = [
                # background
                '#000000', '#CC0000', '#4E9A06', '#C4A000',
                '#3465A4', '#75507B', '#06989A', '#D3D7CF',
                # foreground
                '#555753', '#EF2929', '#8AE234', '#FCE94F',
                '#729FCF', '#729FCF', '#34E2E2', '#EEEEEC'
            ]

            palette = []
            for components in palette_components:
                color = parse_color_rgba(components)
                palette.append(color)

            if len(fcolor)>0 and len(bcolor)>0:
                v.set_colors(parse_color_rgba(fcolor), parse_color_rgba(bcolor), palette)

            if len(conf.FONT)==0:
                conf.FONT = 'monospace'
            else:
                v.set_font(Pango.FontDescription(conf.FONT))
            
            scrollPane = Gtk.ScrolledWindow()            
            scrollPane.connect('button_press_event', lambda *args: True)
            scrollPane.set_property('hscrollbar-policy', Gtk.PolicyType.NEVER)
            tab = NotebookTabLabel("  %s  " % (host.name), self.nbConsole, scrollPane, self.popupMenuTab )
            
            v.connect("child-exited", lambda *args: tab.mark_tab_as_closed())
            v.connect('focus', self.on_tab_focus)
            v.connect('button_press_event', self.on_terminal_click)
            v.connect('key_press_event', self.on_terminal_keypress)            
            v.connect('selection-changed', self.on_terminal_selection)
            
            if conf.TRANSPARENCY > 0 and self.wMain.transparency:
                #v.set_opacity(1 - (conf.TRANSPARENCY / 100)) #posibly a bug in gtk3, set_opacity only works if parent is transparent too (worked just fine in gtk2), 
                #the workaround is to set the background color with alpha channel

                #if bcolor is not set, then use default background color
                c = parse_color_rgba(bcolor if bcolor else DEFAULT_BGCOLOR)
                c.alpha = 1 - (conf.TRANSPARENCY / 100)
                v.set_color_background(c)
            
            v.set_backspace_binding(host.backspace_key)
            v.set_delete_binding(host.delete_key)
            
            scrollPane.show()
            scrollPane.add(v)                        
            v.show()            

            notebook.append_page(scrollPane, tab_label=tab)
            notebook.set_current_page(self.nbConsole.page_num(scrollPane))  
            notebook.set_tab_reorderable(scrollPane, True)
            notebook.set_tab_detachable(scrollPane, True)
            self.wMain.set_focus(v)
            self.on_tab_focus(v)
            self.set_terminal_logger(v, host.log)

            GLib.timeout_add(200, lambda : self.wMain.set_focus(v))
            
            #Dar tiempo a la interfaz para que muestre el terminal
            while Gtk.events_pending():
                Gtk.main_iteration()
            
            v.host = host

            if host.host == '' or host.host == None:
                vte_run(v, SHELL)
            else:
                cmd = SSH_COMMAND
                password = host.password
                if host.type == 'ssh':
                    if len(host.user)==0:
                        host.user = get_username()
                    if host.password == '':
                        cmd = SSH_BIN
                        args = [ SSH_BIN, '-l', host.user, '-p', host.port]
                    else:
                        args = [SSH_COMMAND, host.type, '-l', host.user, '-p', host.port]                                       
                    if host.keep_alive!='0' and host.keep_alive!='':
                        args.append('-o')
                        args.append('ServerAliveInterval=%s' % (host.keep_alive))
                    for t in host.tunnel:
                        if t!="":
                            if t.endswith(":*:*"):
                                args.append("-D")
                                args.append(t[:-4])
                            else:
                                args.append("-L")
                                args.append(t)
                    if host.x11:
                        args.append("-X")
                    if host.agent:
                        args.append("-A")
                    if host.compression:
                        args.append("-C")
                        if host.compressionLevel!='':
                            args.append('-o')
                            args.append('CompressionLevel=%s' % (host.compressionLevel))
                    if host.private_key != None and host.private_key != '':
                        args.append("-i")
                        args.append(host.private_key)
                    if host.extra_params != None and host.extra_params != '':
                        args += shlex.split(host.extra_params)
                    args.append(host.host)
                else:
                    if host.user=='' or host.password=='':
                        password=''
                        cmd = TEL_BIN
                        args = [TEL_BIN]
                    else:
                        args = [SSH_COMMAND, host.type, '-l', host.user]
                    if host.extra_params != None and host.extra_params != '':
                        args += shlex.split(host.extra_params)
                    args += [host.host, host.port]
                v.command = (cmd, args, password)
                #v.fork_command(cmd, args)
                vte_run(v, cmd, args)
                while Gtk.events_pending():
                    Gtk.main_iteration()                                
                
                #esperar 2 seg antes de enviar el pass para dar tiempo a que se levante expect y prevenir que se muestre el pass
                if password!=None and password!='':
                    GLib.timeout_add(2000, self.send_data, v, password)
            
            #esperar 3 seg antes de enviar comandos
            if host.commands!=None and host.commands!='':
                basetime = 700 if len(host.host)==0 else 3000
                lines = []
                for line in host.commands.splitlines():
                    if line.startswith("##D=") and line[4:].isdigit():
                        if len(lines):
                            GLib.timeout_add(basetime, self.send_data, v, "\r".join(lines))
                            lines = []
                        basetime += int(line[4:])
                    else:
                        lines.append(line)
                if len(lines):
                    GLib.timeout_add(basetime, self.send_data, v, "\r".join(lines))
            v.queue_draw()
            
            #guardar datos de consola para clonar consola
            v.host = host
        except Exception as e:
            print("ERROR", e)
            traceback.print_exc()
            msgbox("%s: %s" % (_("Error al conectar con servidor"), sys.exc_info()[1]))

    def send_data(self, terminal, data):
        vte_feed(terminal, '%s\r' % data)
        return False
        
    def initLeftPane(self):
        global groups       

        self.treeModel = Gtk.TreeStore(GObject.TYPE_STRING, GObject.TYPE_PYOBJECT, str, str)
        self.treeServers.set_model(self.treeModel)

        self.treeServers.set_level_indentation(5)
        #self.treeServers.set_grid_lines(Gtk.TreeViewGridLines.HORIZONTAL)

        column = Gtk.TreeViewColumn()
        column.set_title('Servers')
        self.treeServers.append_column( column )

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, expand=False)
        column.add_attribute(renderer, 'stock_id', 2)
        column.add_attribute(renderer, 'cell-background', 3)

        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, expand=True)
        column.add_attribute(renderer, 'text', 0)
        column.add_attribute(renderer, 'cell-background', 3)
        
        self.treeServers.set_has_tooltip(True)
        self.treeServers.connect('query-tooltip', self.on_treeServers_tooltip)
        self.loadConfig()
        self.updateTree()
               
    def on_treeServers_tooltip(self, widget, x, y, keyboard, tooltip):
        x,y = widget.convert_widget_to_bin_window_coords(x, y)
        pos = widget.get_path_at_pos(x, y)
        if pos:
            host = list(widget.get_model()[pos[0]])[1]
            if host:
                text = "<span><b>%s</b>\n%s:%s@%s\n</span><span size='smaller'>%s</span>" % (host.name, host.type, host.user, host.host, host.description)
                tooltip.set_markup(text)
                return True
        return False
        
    def add_shortcut(self, cp, scuts, command, name, default):
        try:
            scuts[cp.get("shortcuts", command)] = name
        except:
            scuts[default] = name

    def loadConfig(self):
        global groups
        
        cp= configparser.RawConfigParser(  )
        cp.read( CONFIG_FILE )
        
        #Leer configuracion general
        try:
            conf.WORD_SEPARATORS = cp.get("options", "word-separators")
            conf.BUFFER_LINES = cp.getint("options", "buffer-lines")
            conf.CONFIRM_ON_EXIT = cp.getboolean("options", "confirm-exit")
            conf.FONT_COLOR = cp.get("options", "font-color")
            conf.BACK_COLOR = cp.get("options", "back-color")
            conf.TRANSPARENCY = cp.getint("options", "transparency")
            conf.PASTE_ON_RIGHT_CLICK = cp.getboolean("options", "paste-right-click")
            conf.CONFIRM_ON_CLOSE_TAB = cp.getboolean("options", "confirm-close-tab")
            conf.CHECK_UPDATES = cp.getboolean("options", "check-updates")
            conf.COLLAPSED_FOLDERS = cp.get("window", "collapsed-folders")
            conf.LEFT_PANEL_WIDTH = cp.getint("window", "left-panel-width")
            conf.WINDOW_WIDTH = cp.getint("window", "window-width")
            conf.WINDOW_HEIGHT = cp.getint("window", "window-height")
            conf.FONT = cp.get("options", "font")
            conf.HIDE_DONATE = cp.getboolean("options", "donate")
            conf.AUTO_COPY_SELECTION = cp.getboolean("options", "auto-copy-selection")
            conf.LOG_PATH = cp.get("options", "log-path")
            conf.VERSION = cp.get("options", "version")
            conf.AUTO_CLOSE_TAB = cp.getint("options", "auto-close-tab")
            conf.SHOW_PANEL = cp.getboolean("window", "show-panel")
            conf.SHOW_TOOLBAR = cp.getboolean("window", "show-toolbar")
            conf.STARTUP_LOCAL = cp.getboolean("options","startup-local")
            conf.LOG_LOCAL = cp.getboolean("options","log-local")
            conf.CONFIRM_ON_CLOSE_TAB_MIDDLE = cp.getboolean("options", "confirm-close-tab-middle")
            conf.TERM = cp.get("options", "term")
            conf.UPDATE_TITLE = cp.getboolean("options", "update-title")
            conf.APP_TITLE = cp.get("options", "app-title") or app_name
        except:
            print ("%s: %s" % (_("Entrada invalida en archivo de configuracion"), sys.exc_info()[1]))
        
        #setup shorcuts
        scuts = {}
        self.add_shortcut(cp, scuts, "copy", _COPY, "CTRL+SHIFT+C") 
        self.add_shortcut(cp, scuts, "paste", _PASTE, "CTRL+SHIFT+V")
        self.add_shortcut(cp, scuts, "copy_all", _COPY_ALL, "CTRL+SHIFT+A") 
        self.add_shortcut(cp, scuts, "save", _SAVE, "CTRL+S") 
        self.add_shortcut(cp, scuts, "find", _FIND, "CTRL+F") 
        self.add_shortcut(cp, scuts, "find_next", _FIND_NEXT, "CTRL+G") 
        self.add_shortcut(cp, scuts, "find_back", _FIND_BACK, "CTRL+H") 
        self.add_shortcut(cp, scuts, "console_previous", _CONSOLE_PREV, "CTRL+SHIFT+TAB")
        self.add_shortcut(cp, scuts, "console_next", _CONSOLE_NEXT, "CTRL+TAB")  
        self.add_shortcut(cp, scuts, "console_close", _CONSOLE_CLOSE, "CTRL+W")  
        self.add_shortcut(cp, scuts, "console_reconnect", _CONSOLE_RECONNECT, "CTRL+N")  
        self.add_shortcut(cp, scuts, "connect", _CONNECT, "CTRL+RETURN")
        self.add_shortcut(cp, scuts, "reset", _CLEAR, "CTRL+SHIFT+K")
        self.add_shortcut(cp, scuts, "clone", _CLONE, "CTRL+SHIFT+D")
        self.add_shortcut(cp, scuts, "new_local", _NEW_LOCAL, "CTRL+SHIFT+N")

        #shortcuts para cambiar consola1-consola9
        for x in range(1,10):
            try:
                scuts[cp.get("shortcuts", "console_%d" % (x) )] = eval("_CONSOLE_%d" % (x))                
            except:
                scuts["ALT+%d" % (x)] = eval("_CONSOLE_%d" % (x))                
        try:
            i = 1            
            while True:
                scuts[cp.get("shortcuts", "shortcut%d" % (i))] = cp.get("shortcuts", "command%d" % (i)).replace('\\n','\n')
                i = i + 1
        except:
            pass
        global shortcuts
        shortcuts = scuts
        
        #Leer lista de hosts        
        groups={}
        for section in cp.sections():
            if not section.startswith("host "):
                continue
            host = cp.options(section)
            try:
                host = HostUtils.load_host_from_ini(cp, section)
                
                if not host.group in groups:                    
                    groups[host.group]=[]
                
                groups[host.group].append( host )
            except:                
                print ("%s: %s" % (_("Entrada invalida en archivo de configuracion"), sys.exc_info()[1]))

    def is_node_collapsed(self, model, path, iter, nodes):
        if self.treeModel.get_value(iter, 1)==None and not self.treeServers.row_expanded(path):
             nodes.append(self.treeModel.get_string_from_iter(iter))

    def get_collapsed_nodes(self):
        nodes=[]
        self.treeModel.foreach(self.is_node_collapsed, nodes)
        return nodes
        
    def set_collapsed_nodes(self):
        self.treeServers.expand_all()
        if self.treeModel.get_iter_first():
            for node in conf.COLLAPSED_FOLDERS.split(","): 
                if node!='':
                    self.treeServers.collapse_row(Gtk.TreePath.new_from_string(node))
        
    def servers_background_color(self):        
        self.color_index += 1        
        return self.color_back1 if self.color_index % 2 else self.color_back2
        
    def updateTree(self):
        for grupo in dict(groups):
            if len(groups[grupo])==0:
                del groups[grupo]
        
        if conf.COLLAPSED_FOLDERS == None:
            conf.COLLAPSED_FOLDERS = ','.join(self.get_collapsed_nodes())
        
        self.menuServers.foreach(self.menuServers.remove)
        self.treeModel.clear()
        
        iconHost = "gtk-network"
        iconDir = "gtk-directory"
        grupos = groups.keys()
        #grupos.sort(lambda x,y: cmp(y,x))
        grupos = sorted(grupos, reverse=True)
        
        for grupo in grupos:
            group = None
            path = ""
            menuNode = self.menuServers
                  
            for folder in grupo.split("/"):
                path = path + '/' + folder
                row = self.get_folder(self.treeModel, '', path)
                if row == None:
                    group = self.treeModel.prepend(group, [folder, None, iconDir, '#fff'])
                else:
                    group = row.iter
                
                menu = self.get_folder_menu(self.menuServers, '', path)
                if menu == None:
                    menu = Gtk.ImageMenuItem(label=folder)
                    menu.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_DIRECTORY, Gtk.IconSize.MENU))
                    menuNode.prepend(menu)
                    menuNode = Gtk.Menu()
                    menu.set_submenu(menuNode)
                    menu.show()
                else:
                    menuNode = menu
                
            groups[grupo].sort(key=operator.attrgetter('name'))
            for host in groups[grupo]:
                self.treeModel.append(group, [host.name, host, iconHost, '#fff'])
                mnuItem = Gtk.ImageMenuItem(label=host.name)
                mnuItem.set_image(Gtk.Image.new_from_icon_name(Gtk.STOCK_NETWORK, Gtk.IconSize.MENU))
                mnuItem.show()
                mnuItem.connect("activate", lambda arg, nb, h: self.addTab(nb, h), self.nbConsole, host) 
                menuNode.append(mnuItem)
                
        self.set_collapsed_nodes()
        conf.COLLAPSED_FOLDERS = None
        self.update_row_color()
        
    def update_row_color(self, node=None):     
        #custom method to get alternating row colors in treeview, as that is not possible with gtk3
        if not node:   
            self.color_index = 0
            rgba = self.treeServers.get_style_context().get_background_color(Gtk.StateFlags.NORMAL)
            self.color_back1 = color_to_hex(rgba)
            self.color_back2 = color_to_hex(rgba, -14)
            i = self.treeModel.get_iter_first()
        else:
            i = self.treeModel.iter_children(node)

        if i:           
            self.treeModel[i][3] = self.servers_background_color()
            if self.treeModel[i][1]==None and self.treeServers.row_expanded(self.treeModel.get_path(i)) and self.treeModel.iter_has_child(i):
                self.update_row_color(i)
       
        i = self.treeModel.iter_next(i) if i else None
        while i:
            self.treeModel[i][3] = self.servers_background_color()
            self.update_row_color(i)          
            i = self.treeModel.iter_next(i)
        
    def get_folder(self, obj, folder, path): 
        if not obj: 
            return None        
        for row in obj:
            if path == folder+'/'+row[0]:
                return row
            i = self.get_folder(row.iterchildren(), folder+'/'+row[0], path)
            if i:
                return i
        
    def get_folder_menu(self, obj, folder, path):
        if not obj or not (isinstance(obj,Gtk.Menu) or isinstance(obj,Gtk.MenuItem)):
            return None
        for item in obj.get_children():
            if path == folder+'/'+item.get_label():
                return item.get_submenu()
            i = self.get_folder_menu(item.get_submenu(), folder+'/'+item.get_label(), path)
            if i:
                return i
                
    def writeConfig(self): 
        global groups
        
        cp= configparser.RawConfigParser( )
        cp.read( CONFIG_FILE + ".tmp" )
        
        cp.add_section("options")
        cp.set("options", "word-separators", conf.WORD_SEPARATORS)        
        cp.set("options", "buffer-lines", conf.BUFFER_LINES)
        cp.set("options", "startup-local", conf.STARTUP_LOCAL)
        cp.set("options", "log-local", conf.LOG_LOCAL)
        cp.set("options", "confirm-exit", conf.CONFIRM_ON_EXIT)
        cp.set("options", "font-color", conf.FONT_COLOR)
        cp.set("options", "back-color", conf.BACK_COLOR)
        cp.set("options", "term", conf.TERM)
        cp.set("options", "transparency", conf.TRANSPARENCY)        
        cp.set("options", "paste-right-click", conf.PASTE_ON_RIGHT_CLICK)
        cp.set("options", "confirm-close-tab", conf.CONFIRM_ON_CLOSE_TAB)
        cp.set("options", "confirm-close-tab-middle", conf.CONFIRM_ON_CLOSE_TAB_MIDDLE)
        cp.set("options", "check-updates", conf.CHECK_UPDATES)
        cp.set("options", "font", conf.FONT)
        cp.set("options", "donate", conf.HIDE_DONATE)
        cp.set("options", "auto-copy-selection", conf.AUTO_COPY_SELECTION)
        cp.set("options", "log-path", conf.LOG_PATH)
        cp.set("options", "version", app_fileversion)
        cp.set("options", "auto-close-tab", conf.AUTO_CLOSE_TAB)
        cp.set("options", "update-title", conf.UPDATE_TITLE)
        cp.set("options", "app-title", conf.APP_TITLE or app_name)

        collapsed_folders = ','.join(self.get_collapsed_nodes())         
        cp.add_section("window")
        cp.set("window", "collapsed-folders", collapsed_folders)
        cp.set("window", "left-panel-width", self.hpMain.get_position())
        cp.set("window", "window-width", -1 if self.wMain.is_maximized() else conf.WINDOW_WIDTH)
        cp.set("window", "window-height", -1 if self.wMain.is_maximized() else conf.WINDOW_HEIGHT)
        cp.set("window", "show-panel", conf.SHOW_PANEL)
        cp.set("window", "show-toolbar", conf.SHOW_TOOLBAR)
        
        i=1
        for grupo in groups:
            for host in groups[grupo]:
                section = "host " + str(i)
                cp.add_section(section)
                HostUtils.save_host_to_ini(cp, section, host)
                i+=1
        
        cp.add_section("shortcuts")
        i=1
        for s in shortcuts:            
            if type(shortcuts[s]) == list:
                cp.set("shortcuts", shortcuts[s][0], s)
            else:
                cp.set("shortcuts", "shortcut%d" % (i), s)
                cp.set("shortcuts", "command%d" % (i), shortcuts[s].replace('\n','\\n'))
                i=i+1
                
        f = open(CONFIG_FILE + ".tmp", "w")
        cp.write(f)
        f.close()
        os.rename(CONFIG_FILE + ".tmp", CONFIG_FILE)

    def on_tab_scroll(self, notebook, event):
        if event.get_scroll_deltas()[2] < 0:
            if notebook.get_current_page() == 0:
                notebook.set_current_page(notebook.get_n_pages()-1)
            else:
                notebook.prev_page()
        else:
            if notebook.get_current_page() == notebook.get_n_pages()-1:
                notebook.set_current_page(0)
            else:
                notebook.next_page()

    def on_tab_focus(self, widget, tab=None, *args):
        if isinstance(widget, Vte.Terminal):
            self.current = widget
        if conf.UPDATE_TITLE and widget != None:
            if isinstance(widget, Vte.Terminal):
                tab_text = widget.get_parent().get_parent().get_tab_label(widget.get_parent()).get_text()
            elif tab != None: #notebok page switched
                tab_text = widget.get_tab_label(tab).get_text() if widget.get_tab_label(tab) else ''
            else:
                tab_text = ''
            if tab_text:
                self.wMain.set_title("%s - %s" % (conf.APP_TITLE or app_name, tab_text.strip()))
            else:
                self.wMain.set_title(conf.APP_TITLE or app_name)

    def split_notebook(self, direction):        
        csp = self.current.get_parent() if self.current!=None else None
        cnb = csp.get_parent() if csp!=None else None
        
        #Separar solo si hay mas de 2 tabs en el notebook actual
        if csp!=None and cnb.get_n_pages()>1:
            #Crear un hpaned, en el hijo 0 dejar el notebook y en el hijo 1 el nuevo notebook
            #El nuevo hpaned dejarlo como hijo del actual parent
            hp = Gtk.HPaned() if direction==HSPLIT else Gtk.VPaned()
            nb = Gtk.Notebook()
            nb.set_group_name("11")
            nb.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)
            nb.connect('button_press_event', self.on_double_click, None)
            nb.connect('page_removed', self.on_page_removed)
            nb.connect("page-added", self.on_page_added)
            nb.connect('switch-page', self.on_tab_focus)
            nb.connect('scroll-event', self.on_tab_scroll)

            nb.set_property("scrollable", True)
            cp  = cnb.get_parent()

            if direction==HSPLIT:
                p = cnb.get_allocated_width()/2
            else:                
                p = cnb.get_allocated_height()/2
            hp.set_position(p)
            hp.set_wide_handle(True)
            
            cp.remove(cnb)
            cp.add(hp)
            hp.add1(cnb)                        
            
            text = cnb.get_tab_label(csp).get_text()
            
            csp.get_parent().remove(csp)
            nb.add(csp)
            csp = nb.get_nth_page(0)
                        
            tab = NotebookTabLabel(text, nb, csp, self.popupMenuTab)
            nb.set_tab_label(csp, tab_label=tab)
            nb.set_tab_reorderable(csp, True)
            nb.set_tab_detachable(csp, True)

            hp.add2(nb)
            nb.show()
            hp.show()
            hp.queue_draw()
            self.current = cnb.get_nth_page(cnb.get_current_page()).get_children()[0]
            self.on_tab_focus(cnb, cnb.get_nth_page(cnb.get_current_page()))

    def find_notebook(self, widget, exclude=None):
        if widget!=exclude and isinstance(widget, Gtk.Notebook):
            return widget
        else:
            if not hasattr(widget, "get_children"):
                return None
            for w in widget.get_children():
                wid = self.find_notebook(w, exclude)
                if wid!=exclude and isinstance(wid, Gtk.Notebook):
                    return wid
            return None

    def find_active_terminal(self, widget):        
        if isinstance(widget, Vte.Terminal) and widget.is_focus():
            return widget
        else:
            if not hasattr(widget, "get_children"):
                return None
                             
            for w in widget.get_children():
                wid = self.find_active_terminal(w)
                if isinstance(wid, Vte.Terminal) and wid.is_focus():
                    return wid
            return None

    def check_notebook_pages(self, widget):
        if widget.get_n_pages()==0:
            #eliminar el notebook solo si queda otro notebook y no quedan tabs en el actual            
            paned = widget.get_parent()            
            if paned==None or paned==self.hpMain:
                return
            container = paned.get_parent()
            save = paned.get_child2() if paned.get_child1()==widget else paned.get_child1()    
            container.remove(paned)
            paned.remove(save)
            container.add(save)
            if widget == self.nbConsole:                
                if isinstance(save, Gtk.Notebook):
                    self.nbConsole = save
                else:
                    self.nbConsole = self.find_notebook(save)
            p = self.nbConsole.get_current_page()
            self.on_tab_focus(self.nbConsole, self.nbConsole.get_nth_page(p), p)

    def on_page_removed(self, widget, *args):
        self.count-=1
        if widget.get_current_page() == -1:
            self.on_tab_focus(widget, None)

        if hasattr(widget, "is_closed") and widget.is_closed:
            #tab has been closed
            self.check_notebook_pages(widget)
        else:
            #tab has been moved to another notebook
            #save a reference to this notebook, on_page_added check if the notebook must be removed
            self.check_notebook = widget

    def on_page_added(self, widget, *args):
        self.count+=1
        if hasattr(self, "check_notebook"):
            self.check_notebook_pages(self.check_notebook)
            delattr(self, "check_notebook")
        
    def show_save_buffer(self, terminal):        
        dlg = Gtk.FileChooserDialog(title=_("Guardar como"), parent=self.wMain, action=Gtk.FileChooserAction.SAVE)
        dlg.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dlg.add_button(Gtk.STOCK_SAVE, Gtk.ResponseType.OK)        
        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_name( os.path.basename("gcm-buffer-%s.txt" % (time.strftime("%Y%m%d%H%M%S")) ))
        if not hasattr(self,'lastPath'):
            self.lastPath = USERHOME_DIR
        dlg.set_current_folder( self.lastPath )
        
        if dlg.run() == Gtk.ResponseType.OK:
            filename = dlg.get_filename()
            self.lastPath = os.path.dirname(filename)            
    
            try:              
                buff,b = terminal.get_text_range(0, 0, terminal.get_property('scrollback-lines')-1, terminal.get_column_count()-1, None, None )
                f = open(filename, "w")
                f.write(buff.strip())
                f.close()
            except:
                dlg.destroy()
                msgbox("%s: %s" % (_("No se puede abrir archivo para escritura"), filename) )
                return
            
        dlg.destroy()
    
    def set_panel_visible(self, visibility):
        if visibility:
            GLib.timeout_add(200, lambda : self.hpMain.set_position(self.hpMain.previous_position if self.hpMain.previous_position>10 else 150))
        else:       
            self.hpMain.previous_position = self.hpMain.get_position()
            GLib.timeout_add(200, lambda : self.hpMain.set_position(0))
        self.get_widget("show_panel").set_active(visibility)
        conf.SHOW_PANEL = visibility
    
    def set_toolbar_visible(self, visibility):
        #self.get_widget("toolbar1").set_visible(visibility)
        if visibility:
            self.get_widget("toolbar1").show()
        else:
            self.get_widget("toolbar1").hide()
        self.get_widget("show_toolbar").set_active(visibility)
        conf.SHOW_TOOLBAR = visibility
        
    #-- Wmain custom methods }

    #-- Wmain.on_wMain_destroy {
    def on_wMain_destroy(self, widget, *args):                
        self.writeConfig()
        Gtk.main_quit()
    #-- Wmain.on_wMain_destroy }

    #-- Wmain.on_wMain_delete_event {
    def on_wMain_delete_event(self, widget, *args):
        (conf.WINDOW_WIDTH, conf.WINDOW_HEIGHT) = self.get_widget("wMain").get_size()
        if conf.CONFIRM_ON_EXIT and self.count>0 and msgconfirm("%s %d %s" % (_("Hay"), self.count, _("consolas abiertas, confirma que desea salir?")) ) != Gtk.ResponseType.OK:
            return True
    #-- Wmain.on_wMain_delete_event }

    #-- Wmain.on_guardar_como1_activate {
    def on_guardar_como1_activate(self, widget, *args):        
        term = self.find_active_terminal(self.hpMain)
        if term == None:
            term = self.current
        if term != None:
            self.show_save_buffer(term)
        
    #-- Wmain.on_guardar_como1_activate }

    #-- Wmain.on_importar_servidores1_activate {
    def on_importar_servidores1_activate(self, widget, *args):
        filename = show_open_dialog(parent=self.wMain, title=_("Abrir"), action=Gtk.FileChooserAction.OPEN)
        if filename != None:            
            password = inputbox(_('Importar Servidores'), _('Ingrese clave: '), password=True)
            if password == None:
                return                                                
            
            #abrir archivo con lista de servers y cargarlos en el arbol
            try:
                cp= configparser.RawConfigParser( )
                cp.read( filename )
            
                #validar el pass
                s = decrypt(password, cp.get("gcm", "gcm"))
                if (s != password[::-1]):
                    msgbox(_("Clave invalida"))
                    return
            
                if msgconfirm(_(u'Se sobreescribirá la lista de servidores, continuar?')) != Gtk.ResponseType.OK:
                    return
                    
                grupos={}
                for section in cp.sections():
                    if not section.startswith("host "):
                        continue                    
                    host = HostUtils.load_host_from_ini(cp, section, password)
        
                    if not host.group in grupos:
                        grupos[host.group]=[]  
        
                    grupos[host.group].append( host )
            except:                
                msgbox(_("Archivo invalido"))
                return
            #sobreescribir lista de hosts
            global groups
            groups=grupos
            
            self.updateTree()
    #-- Wmain.on_importar_servidores1_activate }

    #-- Wmain.on_exportar_servidores1_activate {
    def on_exportar_servidores1_activate(self, widget, *args):
        filename = show_open_dialog(parent=self.wMain, title=_("Guardar como"), action=Gtk.FileChooserAction.SAVE)
        if filename != None:
            password = inputbox(_('Exportar Servidores'), _('Ingrese clave: '), password=True)
            if password == None:
                return
                
            try:
                cp= configparser.RawConfigParser( )
                cp.read( filename + ".tmp" )
                i=1
                cp.add_section("gcm")
                cp.set("gcm", "gcm", encrypt(password, password[::-1]))
                global groups
                for grupo in groups:
                    for host in groups[grupo]:
                        section = "host " + str(i)
                        cp.add_section(section)
                        HostUtils.save_host_to_ini(cp, section, host, password)                        
                        i+=1
                f = open(filename + ".tmp", "w")
                cp.write(f)
                f.close()
                os.rename(filename + ".tmp", filename)
            except:
                msgbox(_("Archivo invalido"))
    #-- Wmain.on_exportar_servidores1_activate }

    #-- Wmain.on_salir1_activate {
    def on_salir1_activate(self, widget, *args):
        (conf.WINDOW_WIDTH, conf.WINDOW_HEIGHT) = self.get_widget("wMain").get_size()
        self.writeConfig()
        Gtk.main_quit()
    #-- Wmain.on_salir1_activate }

    #-- Wmain.on_show_toolbar_activate {
    def on_show_toolbar_toggled(self, widget, *args):
        self.set_toolbar_visible(widget.get_active())
    #-- Wmain.on_show_toolbar_activate }

    #-- Wmain.on_show_panel_activate {
    def on_show_panel_toggled(self, widget, *args):
        self.set_panel_visible(widget.get_active())
    #-- Wmain.on_show_panel_activate }
    
    #-- Wmain.on_acerca_de1_activate {
    def on_acerca_de1_activate(self, widget, *args):
        w_about = Wabout()              
    #-- Wmain.on_acerca_de1_activate }

    #-- Wmain.on_double_click {
    def on_double_click(self, widget, event, *args):
        if event.type in [Gdk.EventType._2BUTTON_PRESS, Gdk.EventType._3BUTTON_PRESS] and event.button == 1:
            if isinstance(widget, Gtk.Notebook):                
                pos = event.x + widget.get_allocation().x
                size = widget.get_tab_label(widget.get_nth_page(widget.get_n_pages()-1)).get_allocation()
                if pos <= size.x + size.width + 8 or event.x >= widget.get_allocation().width - widget.style_get_property("scroll-arrow-hlength"):
                    return True
            if isinstance(widget, Gtk.Toolbar) and widget.get_drop_index(event.x,event.y) < widget.get_n_items():
                return True
            self.addTab(widget if isinstance(widget, Gtk.Notebook) else self.nbConsole, 'local')
            return True
    #-- Wmain.on_double_click }

    #-- Wmain.on_btnLocal_clicked {
    def on_btnLocal_clicked(self, widget, *args):        
        if self.current != None and self.current.get_parent()!=None and isinstance(self.current.get_parent().get_parent(), Gtk.Notebook):
            ntbk = self.current.get_parent().get_parent()
        else:
            ntbk = self.nbConsole
        self.addTab(ntbk, 'local')
    #-- Wmain.on_btnLocal_clicked }

    #-- Wmain.on_btnConnect_clicked {
    def on_btnConnect_clicked(self, widget, *args):
        if self.treeServers.get_selection().get_selected()[1]!=None:
            if not self.treeModel.iter_has_child(self.treeServers.get_selection().get_selected()[1]):
                self.on_tvServers_row_activated(self.treeServers)
            else:
                selected = self.treeServers.get_selection().get_selected()[1] 
                group = self.treeModel.get_value(selected,0)       
                parent_group = self.get_group(selected)
                if parent_group != '':
                    group = parent_group + '/' + group
                    
                for g in groups:
                    if g == group or g.startswith(group+'/'):
                        for host in groups[g]:                    
                            self.addTab(self.nbConsole, host)
    #-- Wmain.on_btnConnect_clicked }

    #-- Wmain.on_btnAdd_clicked {
    def on_btnAdd_clicked(self, widget, *args):
        group=""
        if self.treeServers.get_selection().get_selected()[1]!=None:
            selected = self.treeServers.get_selection().get_selected()[1]            
            group = self.get_group(selected)
            if self.treeModel.iter_has_child(self.treeServers.get_selection().get_selected()[1]):
                selected = self.treeServers.get_selection().get_selected()[1] 
                group = self.treeModel.get_value(selected,0)
                parent_group = self.get_group(selected)
                if parent_group != '':
                    group = parent_group + '/' + group                    
        wHost = Whost()
        wHost.init(group)
        self.updateTree()
    #-- Wmain.on_btnAdd_clicked }

    def get_group(self, i):
        if self.treeModel.iter_parent(i):
            p = self.get_group(self.treeModel.iter_parent(i))
            return (p+'/' if p!='' else '') + self.treeModel.get_value(self.treeModel.iter_parent(i),0)
        else:
            return ''
            
    #-- Wmain.on_bntEdit_clicked {
    def on_bntEdit_clicked(self, widget, *args):
        if self.treeServers.get_selection().get_selected()[1]!=None and not self.treeModel.iter_has_child(self.treeServers.get_selection().get_selected()[1]):
            selected = self.treeServers.get_selection().get_selected()[1]
            host = self.treeModel.get_value(selected,1)
            wHost = Whost()
            wHost.init(host.group, host)
            #self.updateTree()            
    #-- Wmain.on_bntEdit_clicked }

    #-- Wmain.on_btnDel_clicked {
    def on_btnDel_clicked(self, widget, *args):
        if self.treeServers.get_selection().get_selected()[1]!=None:
            if not self.treeModel.iter_has_child(self.treeServers.get_selection().get_selected()[1]):
                #Eliminar solo el nodo
                name = self.treeModel.get_value(self.treeServers.get_selection().get_selected()[1],0)
                if msgconfirm("%s [%s]?" % (_("Confirma que desea eliminar el host"), name) ) == Gtk.ResponseType.OK:
                    host = self.treeModel.get_value(self.treeServers.get_selection().get_selected()[1],1)
                    groups[host.group].remove(host)
                    self.updateTree()
            else:                
                #Eliminar todo el grupo                
                group = self.get_group(self.treeModel.iter_children(self.treeServers.get_selection().get_selected()[1]))
                if msgconfirm("%s [%s]?" % (_("Confirma que desea eliminar todos los hosts del grupo"), group) ) == Gtk.ResponseType.OK:                                
                    try:
                        del groups[group]
                    except:
                        pass
                    for h in dict(groups):
                        if h.startswith(group+'/'):
                            del groups[h]
                    self.updateTree()
        self.writeConfig()
    #-- Wmain.on_btnDel_clicked }

    #-- Wmain.on_btnHSplit_clicked {
    def on_btnHSplit_clicked(self, widget, *args):
        self.split_notebook(HSPLIT)
    #-- Wmain.on_btnHSplit_clicked }

    #-- Wmain.on_btnVSplit_clicked {
    def on_btnVSplit_clicked(self, widget, *args):
        self.split_notebook(VSPLIT)
    #-- Wmain.on_btnVSplit_clicked }

    #-- Wmain.on_btnUnsplit_clicked {
    def on_btnUnsplit_clicked(self, widget, *args):
        wid = self.find_notebook(self.hpMain, self.nbConsole)
        while wid!=None:
            #Mover los tabs al notebook principal           
            while wid.get_n_pages()!=0:
                csp = wid.get_nth_page(0)
                text = wid.get_tab_label(csp).get_text()
                csp.get_parent().remove(csp)
                self.nbConsole.add(csp)
                csp = self.nbConsole.get_nth_page(self.nbConsole.get_n_pages()-1)
                tab = NotebookTabLabel(text, self.nbConsole, csp, self.popupMenuTab )
                self.nbConsole.set_tab_label(csp, tab_label=tab)                       
                self.nbConsole.set_tab_reorderable(csp, True)
                self.nbConsole.set_tab_detachable(csp, True)
            wid = self.find_notebook(self.hpMain, self.nbConsole)
        self.on_tab_focus(self.nbConsole, self.nbConsole.get_nth_page(self.nbConsole.get_current_page()))
    #-- Wmain.on_btnUnsplit_clicked }

    #-- Wmain.on_btnConfig_clicked {
    def on_btnConfig_clicked(self, widget, *args):
        wConfig = Wconfig()        
    #-- Wmain.on_btnConfig_clicked }

    #-- Wmain.on_btnDonate_clicked {
    def on_btnDonate_clicked(self, widget, *args):
        with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
            f.write(b'<html> \
                     <body onload="document.forms[0].submit()"> \
                     <form action="https://www.paypal.com/cgi-bin/webscr" method="post"> \
                     <input type="hidden" name="cmd" value="_s-xclick"> \
                     <input type="hidden" name="hosted_button_id" value="10257762"> \
                     </form> \
                     </body> \
                     </html>')
            f.flush()
            if os.name == "nt":
                os.filestart(f.name)
            elif os.name == "posix":
                os.system("/usr/bin/xdg-open %s" % (f.name))
            
    #-- Wmain.on_btnDonate_clicked }
    
    #-- Wmain.on_txtSearch_focus {
    def on_txtSearch_focus(self, widget, *args):
        if widget.get_text() == _('buscar...'):
            widget.override_color(Gtk.StateFlags.NORMAL, parse_color_rgba('black'))
            widget.set_text('')
    #-- Wmain.on_txtSearch_focus }

    #-- Wmain.on_txtSearch_focus_out_event {
    def on_txtSearch_focus_out_event(self, widget, *args):
        if widget.get_text() == '':
            widget.override_color(Gtk.StateFlags.NORMAL, parse_color_rgba('darkgray'))
            widget.set_text(_('buscar...'))
    #-- Wmain.on_txtSearch_focus_out_event }

    #-- Wmain.on_btnSearchBack_clicked {
    def on_btnSearchBack_clicked(self, widget, *args):
        if self.init_search():       
            self.find_word(backwards=True)
    #-- Wmain.on_btnSearchBack_clicked }

    #-- Wmain.on_btnSearch_clicked {
    def on_btnSearch_clicked(self, widget, *args):        
        if self.init_search():               
            self.find_word()
    #-- Wmain.on_btnSearch_clicked }

    def on_btnSearch_key_press(self, widget, event, *args):
        if event.state & (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK): return
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            if self.init_search():
                self.find_word()
        elif event.keyval == Gdk.KEY_Escape:
            widget.set_text('')
            self.init_search()


    #-- Wmain.on_btnCluster_clicked {
    def on_btnCluster_clicked(self, widget, *args):
        create = False
        if hasattr(self, 'wCluster'):
            if not self.wCluster.get_property("visible"):
                self.wCluster.destroy()        
                create = True
        else:
            create = True
            
        if not create:
            return True
        
        #obtener lista de consolas abiertas
        consoles = []
        global wMain
        obj = wMain.hpMain        
        s = []
        s.append(obj)
        while len(s) > 0:
            obj = s.pop()
            #agregar hijos de p a s 
            if hasattr(obj, "get_children"):
                for w in obj.get_children():
                    if isinstance(w, Gtk.Notebook) or hasattr(w, "get_children"):
                        s.append(w)
            
            if isinstance(obj, Gtk.Notebook):
                n = obj.get_n_pages()
                for i in range(0,n):
                    terminal = obj.get_nth_page(i).get_child()                    
                    title = obj.get_tab_label(obj.get_nth_page(i)).get_text()
                    consoles.append( (title, terminal) )                
        
        if len(consoles)==0:
            msgbox(_("No hay consolas abiertas"))
            return True
            
        self.wCluster = Wcluster(terms=consoles).get_widget('wCluster')  
        return True                 
    #-- Wmain.on_btnCluster_clicked }

    #-- Wmain.on_hpMain_button_press_event {
    def on_hpMain_button_press_event(self, widget, event, *args):
        if event.type in [Gdk.EventType._2BUTTON_PRESS] and not self.row_activated:
            p = self.hpMain.get_position()
            self.set_panel_visible(p==0) 
        self.row_activated = False
    #-- Wmain.on_hpMain_button_press_event }

    #-- Wmain.on_tvServers_row_activated {
    def on_tvServers_row_activated(self, widget, *args):
        self.row_activated = True       
        if not self.treeModel.iter_has_child(widget.get_selection().get_selected()[1]):  
            selected = widget.get_selection().get_selected()[1]
            host = self.treeModel.get_value(selected,1)
            self.addTab(self.nbConsole, host)
        
    #-- Wmain.on_tvServers_row_activated }

    def on_tvServers_row_collapsed(self, widget, *args):
        self.update_row_color()

    def on_tvServers_row_expanded(self, widget, *args):
        self.update_row_color()

    def on_tvServers_style_updated(self, widget, *args):
        self.update_row_color()
        
    #-- Wmain.on_tvServers_button_press_event {
    def on_tvServers_button_press_event(self, widget, event, *args):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            x = int(event.x)
            y = int(event.y)            
            pthinfo = self.treeServers.get_path_at_pos(x, y)
            if pthinfo is None:
                self.popupMenuFolder.mnuDel.hide()
                self.popupMenuFolder.mnuEdit.hide()
                self.popupMenuFolder.mnuCopyAddress.hide()
                self.popupMenuFolder.mnuDup.hide()
            else:
                path, col, cellx, celly = pthinfo                                
                if self.treeModel.iter_children(self.treeModel.get_iter(path)):                                    
                    self.popupMenuFolder.mnuEdit.hide()
                    self.popupMenuFolder.mnuCopyAddress.hide()
                    self.popupMenuFolder.mnuDup.hide()
                else:
                    self.popupMenuFolder.mnuEdit.show()
                    self.popupMenuFolder.mnuCopyAddress.show()
                    self.popupMenuFolder.mnuDup.show()
                self.popupMenuFolder.mnuDel.show()
                self.treeServers.grab_focus()
                self.treeServers.set_cursor( path, col, 0)
            self.popupMenuFolder.popup( None, None, None, None, event.button, event.time)
            return True
        else:
            return event.type == Gdk.EventType._2BUTTON_PRESS or event.type == Gdk.EventType._3BUTTON_PRESS
    #-- Wmain.on_tvServers_button_press_event }

class Host():
    def __init__(self, *args):
        try:
            self.i = 0
            self.group = self.get_arg(args, None)
            self.name =  self.get_arg(args, None)
            self.description =  self.get_arg(args, None)            
            self.host =  self.get_arg(args, None)
            self.user =   self.get_arg(args, None)
            self.password = self.get_arg(args, None)
            self.private_key = self.get_arg(args, None)
            self.port = self.get_arg(args, 22)
            self.tunnel = self.get_arg(args, '').split(",")
            self.type = self.get_arg(args, 'ssh')
            self.commands = self.get_arg(args, None)
            self.keep_alive = self.get_arg(args, 0)
            self.font_color = self.get_arg(args, '')
            self.back_color = self.get_arg(args, '')
            self.x11 = self.get_arg(args, False)
            self.agent = self.get_arg(args, False)
            self.compression = self.get_arg(args,False)
            self.compressionLevel = self.get_arg(args,'')
            self.extra_params = self.get_arg(args, '')
            self.log = self.get_arg(args, False)
            self.backspace_key = self.get_arg(args, int(Vte.EraseBinding.AUTO))
            self.delete_key = self.get_arg(args, int(Vte.EraseBinding.AUTO))
            self.term = self.get_arg(args, '')
        except:
            pass
       

    def get_arg(self, args, default):
        arg = args[self.i] if len(args)>self.i else default
        self.i +=1
        return arg

    def __repr__(self):
        return "group=[%s],\t name=[%s],\t host=[%s],\t type=[%s]" % (self.group, self.name, self.host, self.type)

    def tunnel_as_string(self):
        return ",".join(self.tunnel)

    def clone(self):
        return Host(self.group, self.name, self.description, self.host, self.user, self.password, self.private_key, self.port, self.tunnel_as_string(), self.type, self.commands, self.keep_alive, self.font_color, self.back_color, self.x11, self.agent, self.compression, self.compressionLevel, self.extra_params, self.log, self.backspace_key, self.delete_key, self.term)

class HostUtils:
    @staticmethod
    def get_val(cp, section, name, default):
        try:
            return cp.get(section, name) if type(default)!=type(True) else cp.getboolean(section, name)
        except:
            return default
    
    @staticmethod
    def load_host_from_ini(cp, section, pwd=''):
        if pwd=='':
            pwd = get_password()
        group = cp.get(section, "group")
        name = cp.get(section, "name")
        host = cp.get(section, "host")
        user = cp.get(section, "user")
        password = decrypt(pwd, cp.get(section, "pass"))
        description = HostUtils.get_val(cp, section, "description", "")
        private_key = HostUtils.get_val(cp, section, "private_key", "")
        port = HostUtils.get_val(cp, section, "port", "22")
        tunnel = HostUtils.get_val(cp, section, "tunnel", "")
        ctype = HostUtils.get_val(cp, section, "type", "ssh")
        commands = HostUtils.get_val(cp, section, "commands", "").replace('\x00', '\n').replace('\\n', '\n')
        keepalive = HostUtils.get_val(cp, section, "keepalive", "")
        fcolor = HostUtils.get_val(cp, section, "font-color", "")
        bcolor = HostUtils.get_val(cp, section, "back-color", "")
        x11 = HostUtils.get_val(cp, section, "x11", False)
        agent = HostUtils.get_val(cp, section, "agent", False)
        compression = HostUtils.get_val(cp, section, "compression", False)
        compressionLevel = HostUtils.get_val(cp, section, "compression-level", "")
        extra_params = HostUtils.get_val(cp, section, "extra_params", "")
        log = HostUtils.get_val(cp, section, "log", False)
        backspace_key = int(HostUtils.get_val(cp, section, "backspace-key", int(Vte.EraseBinding.AUTO)))
        delete_key = int(HostUtils.get_val(cp, section, "delete-key", int(Vte.EraseBinding.AUTO)))
        term = HostUtils.get_val(cp, section, "term", "")
        h = Host(group, name, description, host, user, password, private_key, port, tunnel, ctype, commands, keepalive, fcolor, bcolor, x11, agent, compression, compressionLevel,  extra_params, log, backspace_key, delete_key, term)
        return h

    @staticmethod
    def save_host_to_ini(cp, section, host, pwd=''):
        if pwd=='':
            pwd = get_password()
        cp.set(section, "group", host.group)
        cp.set(section, "name", host.name)
        cp.set(section, "description", host.description)
        cp.set(section, "host", host.host)
        cp.set(section, "user", host.user)
        cp.set(section, "pass", encrypt(pwd, host.password))
        cp.set(section, "private_key", host.private_key)
        cp.set(section, "port", host.port)
        cp.set(section, "tunnel", host.tunnel_as_string())
        cp.set(section, "type", host.type)
        cp.set(section, "commands", host.commands.replace('\n', '\\n'))
        cp.set(section, "keepalive", host.keep_alive)
        cp.set(section, "font-color", host.font_color)
        cp.set(section, "back-color", host.back_color)
        cp.set(section, "x11", host.x11)
        cp.set(section, "agent", host.agent)
        cp.set(section, "compression", host.compression)
        cp.set(section, "compression-level", host.compressionLevel)
        cp.set(section, "extra_params", host.extra_params)
        cp.set(section, "log", host.log)
        cp.set(section, "backspace-key", host.backspace_key)
        cp.set(section, "delete-key", host.delete_key)
        cp.set(section, "term", host.term)

class Whost(SimpleGladeApp):

    def __init__(self, path="gnome-connection-manager.glade",
                 root="wHost",
                 domain=domain_name, **kwargs):
        path = os.path.join(glade_dir, path)
        SimpleGladeApp.__init__(self, path, root, domain, parent=wMain.window)
        
        self.treeModel = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_STRING)
        self.treeTunel.set_model(self.treeModel)
        column = Gtk.TreeViewColumn(_("Local"), Gtk.CellRendererText(), text=0)
        self.treeTunel.append_column( column )        
        column = Gtk.TreeViewColumn(_("Host"), Gtk.CellRendererText(), text=1)
        self.treeTunel.append_column( column )        
        column = Gtk.TreeViewColumn(_("Remoto"), Gtk.CellRendererText(), text=2)
        self.treeTunel.append_column( column )        


    #-- Whost.new {
    def new(self):
        global groups
        
        self.cmbGroup = self.get_widget("cmbGroup")
        #self.cmbGroup.set_model(Gtk.ListStore(str))
        self.txtName = self.get_widget("txtName")
        self.txtDescription = self.get_widget("txtDescription")
        self.txtHost = self.get_widget("txtHost")
        self.cmbType = self.get_widget("cmbType")        
        self.txtUser = self.get_widget("txtUser")
        self.txtPass = self.get_widget("txtPassword")
        self.txtPrivateKey = self.get_widget("txtPrivateKey")
        self.btnBrowse = self.get_widget("btnBrowse")
        self.txtPort = self.get_widget("txtPort")
        self.cmbGroup.remove_all()
        for group in groups:
            self.cmbGroup.append_text(group)
        self.isNew = True
        
        self.chkDynamic = self.get_widget("chkDynamic")
        self.txtLocalPort = self.get_widget("txtLocalPort")
        self.txtRemoteHost = self.get_widget("txtRemoteHost")
        self.txtRemotePort = self.get_widget("txtRemotePort")
        self.treeTunel = self.get_widget("treeTunel")
        self.txtComamnds = self.get_widget("txtCommands")
        self.chkComamnds = self.get_widget("chkCommands")
        buf = self.txtComamnds.get_buffer()
        buf.create_tag('DELAY1', style=Pango.Style.ITALIC, foreground='darkgray')
        buf.create_tag('DELAY2', style=Pango.Style.ITALIC, foreground='cadetblue')
        buf.connect("changed", self.update_texttags)
        self.chkKeepAlive = self.get_widget("chkKeepAlive")
        self.txtKeepAlive = self.get_widget("txtKeepAlive")
        self.btnFColor = self.get_widget("btnFColor")
        self.btnBColor = self.get_widget("btnBColor")
        self.chkX11 = self.get_widget("chkX11")
        self.chkAgent = self.get_widget("chkAgent")
        self.chkCompression = self.get_widget("chkCompression")
        self.txtCompressionLevel = self.get_widget("txtCompressionLevel")
        self.txtExtraParams = self.get_widget("txtExtraParams")
        self.chkLogging = self.get_widget("chkLogging")
        self.cmbBackspace = self.get_widget("cmbBackspace")
        self.cmbDelete = self.get_widget("cmbDelete")
        self.txtTerm = self.get_widget("txtTerm")
        self.cmbType.set_active(0)
        self.cmbBackspace.set_active(0)
        self.cmbDelete.set_active(0)
    #-- Whost.new }

    #-- Whost custom methods {
    def init(self, group, host=None):
        self.cmbGroup.get_child().set_text(group)
        if host == None:
            self.isNew = True            
            return
        
        self.isNew = False
        self.oldGroup = group
        self.txtName.set_text(host.name)
        self.oldName = host.name
        self.txtDescription.set_text(host.description)
        self.txtHost.set_text(host.host)                
        i =  self.cmbType.get_model().get_iter_first()
        while i!=None:                    
            if (host.type == self.cmbType.get_model()[i][0]):
                self.cmbType.set_active_iter(i)
                break
            else:
                i = self.cmbType.get_model().iter_next(i)
        self.txtUser.set_text(host.user)
        self.txtPass.set_text(host.password)
        self.txtPrivateKey.set_text(host.private_key)
        self.txtPort.set_text(host.port)
        for t in host.tunnel:
            if t!="":
                tun = t.split(":")
                tun.append(t)
                self.treeModel.append(  tun )
        self.txtCommands.set_sensitive(False)
        self.chkCommands.set_active(False)
        if host.commands!='' and host.commands!=None:
            self.txtCommands.get_buffer().set_text(host.commands)
            self.txtCommands.set_sensitive(True)
            self.chkCommands.set_active(True)
        use_keep_alive = host.keep_alive!='' and host.keep_alive!='0' and host.keep_alive!=None
        self.txtKeepAlive.set_sensitive(use_keep_alive)
        self.chkKeepAlive.set_active(use_keep_alive)
        self.txtKeepAlive.set_text(host.keep_alive)
        if host.font_color!='' and host.font_color!=None and host.back_color!='' and host.back_color!=None:
            self.get_widget("chkDefaultColors").set_active(False)
            self.btnFColor.set_sensitive(True)
            self.btnBColor.set_sensitive(True)
            fcolor=host.font_color
            bcolor=host.back_color
        else:
            self.get_widget("chkDefaultColors").set_active(True)
            self.btnFColor.set_sensitive(False)
            self.btnBColor.set_sensitive(False)
            fcolor=DEFAULT_FGCOLOR
            bcolor=DEFAULT_BGCOLOR
 
        self.btnFColor.set_rgba(parse_color_rgba(fcolor))
        self.btnBColor.set_rgba(parse_color_rgba(bcolor))
        
        self.btnFColor.selected_color=fcolor
        self.btnBColor.selected_color=bcolor
        self.chkX11.set_active(host.x11)   
        self.chkAgent.set_active(host.agent)
        self.chkCompression.set_active(host.compression)
        self.txtCompressionLevel.set_text(host.compressionLevel)
        self.txtExtraParams.set_text(host.extra_params)
        self.chkLogging.set_active(host.log)
        self.cmbBackspace.set_active(host.backspace_key)
        self.cmbDelete.set_active(host.delete_key)
        self.update_texttags()
        self.txtTerm.set_text(host.term)
        
    def update_texttags(self, *args):
        buf = self.txtCommands.get_buffer()
        text_iter = buf.get_start_iter()
        buf.remove_all_tags(text_iter, buf.get_end_iter())
        while True:
            found = text_iter.forward_search("##D=",0, None)
            if not found: 
                break
            start, end = found
            n = end.copy()
            end.forward_line()
            if buf.get_text(n, end, False).rstrip().isdigit():
                buf.apply_tag_by_name("DELAY1", start, n)
                buf.apply_tag_by_name("DELAY2", n, end)
            text_iter = end
            
    #-- Whost custom methods }

    #-- Whost.on_cancelbutton1_clicked {
    def on_cancelbutton1_clicked(self, widget, *args):
        self.get_widget("wHost").destroy()
    #-- Whost.on_cancelbutton1_clicked }


    #-- Whost.on_okbutton1_clicked {
    def on_okbutton1_clicked(self, widget, *args):
        group = self.cmbGroup.get_active_text().strip()
        name = self.txtName.get_text().strip()
        description = self.txtDescription.get_text().strip()
        host = self.txtHost.get_text().strip()
        ctype = self.cmbType.get_active_text().strip()
        user = self.txtUser.get_text().strip()
        password = self.txtPass.get_text().strip()
        private_key = self.txtPrivateKey.get_text().strip()
        port = self.txtPort.get_text().strip()
        buf = self.txtCommands.get_buffer()
        commands = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip() if self.chkCommands.get_active() else ""
        keepalive = self.txtKeepAlive.get_text().strip()
        if self.get_widget("chkDefaultColors").get_active():
            fcolor=""
            bcolor=""
        else:
            fcolor = self.btnFColor.selected_color
            bcolor = self.btnBColor.selected_color
        
        x11 = self.chkX11.get_active()
        agent = self.chkAgent.get_active()
        compression = self.chkCompression.get_active()
        compressionLevel = self.txtCompressionLevel.get_text().strip()
        extra_params = self.txtExtraParams.get_text()
        log = self.chkLogging.get_active()
        backspace_key = self.cmbBackspace.get_active()
        delete_key = self.cmbDelete.get_active()
        
        if ctype == "":
            ctype = "ssh"
        tunnel=""
        
        if ctype=="ssh":
            for x in self.treeModel:
                tunnel = '%s,%s' % (x[3], tunnel)
            tunnel=tunnel[:-1]
        
        #Validar datos
        if group=="" or name=="" or (host=="" and ctype!='local'):
            msgbox(_("Los campos grupo, nombre y host son obligatorios"))
            return
        
        if not (port and port.isdigit() and 1 <= int(port) <= 65535):
            msgbox(_("Puerto invalido"))
            return
        
        term = self.txtTerm.get_text()        

        host = Host(group, name, description, host, user, password, private_key, port, tunnel, ctype, commands, keepalive, fcolor, bcolor, x11, agent, compression, compressionLevel,  extra_params, log, backspace_key, delete_key, term)
                    
        try:
            #Guardar                
            if not group in groups: #not groups.has_key(group):
                groups[group]=[]   
            
            if self.isNew:
                for h in groups[group]:
                    if h.name == name:
                        msgbox("%s [%s] %s [%s]" % (_("El nombre"), name, _("ya existe para el grupo"), group))
                        return
                #agregar host a grupo
                groups[group].append( host )
            else:
                if self.oldGroup!=group:
                    #revisar que no este el nombre en el nuevo grupo
                    if not group in groups: #if not groups.has_key(group):
                        groups[group] = [ host ]
                    else:
                        for h in groups[group]:
                            if h.name == name:
                                msgbox("%s [%s] %s [%s]" % (_("El nombre"), name, _("ya existe para el grupo"), group))
                                return
                        groups[group].append( host )
                        for h in groups[self.oldGroup]:
                            if h.name == self.oldName:
                                groups[self.oldGroup].remove(h)
                                break
                else:
                    if self.oldName!=name:                        
                        for h in groups[self.oldGroup]:
                            if h.name == name:
                                msgbox("%s [%s] %s [%s]" % (_("El nombre"), name, _("ya existe para el grupo"), group))
                                return
                        for h in groups[self.oldGroup]:
                            if h.name == self.oldName:
                                index = groups[self.oldGroup].index(h)
                                groups[self.oldGroup][ index ] = host
                                break
                    else:
                        for h in groups[self.oldGroup]:
                            if h.name == self.oldName:
                                index = groups[self.oldGroup].index(h)
                                groups[self.oldGroup][ index ] = host
                                break
        except:
            msgbox("%s [%s]" % (_("Error al guardar el host. Descripcion"), sys.exc_info()[1]))            
        
        global wMain
        wMain.updateTree()
        wMain.writeConfig()
        
        self.get_widget("wHost").destroy()
    #-- Whost.on_okbutton1_clicked }

    #-- Whost.on_cmbType_changed {
    def on_cmbType_changed(self, widget, *args):
        is_local = widget.get_active_text()=="local"
        self.txtUser.set_sensitive(not is_local)
        self.txtPassword.set_sensitive(not is_local)
        self.txtPort.set_sensitive(not is_local)
        self.txtHost.set_sensitive(not is_local)
        self.txtExtraParams.set_sensitive(not is_local)
        
        if widget.get_active_text()=="ssh":
            self.get_widget("table2").show()
            self.txtKeepAlive.set_sensitive(True)
            self.chkKeepAlive.set_sensitive(True)
            self.chkX11.set_sensitive(True)
            self.chkAgent.set_sensitive(True)
            self.chkCompression.set_sensitive(True)
            self.txtCompressionLevel.set_sensitive(self.chkCompression.get_active())
            self.txtPrivateKey.set_sensitive(True)
            self.btnBrowse.set_sensitive(True)
            port = "22"
        else:
            self.get_widget("table2").hide()
            self.txtKeepAlive.set_text('0')
            self.txtKeepAlive.set_sensitive(False)
            self.chkKeepAlive.set_sensitive(False)
            self.chkX11.set_sensitive(False)
            self.chkAgent.set_sensitive(False)
            self.chkCompression.set_sensitive(False)
            self.txtCompressionLevel.set_sensitive(False)
            self.txtPrivateKey.set_sensitive(False)
            self.btnBrowse.set_sensitive(False)
            port = "23"
            if is_local:
                self.txtUser.set_text('')
                self.txtPassword.set_text('')
                self.txtPort.set_text('')
                self.txtHost.set_text('')
        self.txtPort.set_text(port)
    #-- Whost.on_cmbType_changed }

    #-- Whost.on_chkKeepAlive_toggled {
    def on_chkKeepAlive_toggled(self, widget, *args):
        if (widget.get_active()):
            self.txtKeepAlive.set_text('120')
        else:
            self.txtKeepAlive.set_text('0')
        self.txtKeepAlive.set_sensitive(widget.get_active())
    #-- Whost.on_chkKeepAlive_toggled }

    #-- Whost.on_chkCompression_toggled {
    def on_chkCompression_toggled(self, widget, *args):
        self.txtCompressionLevel.set_sensitive(widget.get_active())
    #-- Whost.on_chkCompression_toggled }
    

    #-- Whost.on_chkDynamic_toggled {
    def on_chkDynamic_toggled(self, widget, *args):
        self.txtRemoteHost.set_sensitive(not widget.get_active())
        self.txtRemotePort.set_sensitive(not widget.get_active())
    #-- Whost.on_chkDynamic_toggled }
    
    #-- Whost.on_btnAdd_clicked {
    def on_btnAdd_clicked(self, widget, *args):                
        local = self.txtLocalPort.get_text().strip()
        host = self.txtRemoteHost.get_text().strip()        
        remote = self.txtRemotePort.get_text().strip()
        
        if self.chkDynamic.get_active():
            host = '*'
            remote = '*'
        
        #Validar datos del tunel
        if host == "":
            msgbox(_("Debe ingresar host remoto"))
            return
            
        for x in self.treeModel:
            if x[0] == local:
                msgbox(_("Puerto local ya fue asignado"))
                return
                        
        tunel = self.treeModel.append( [local, host, remote, '%s:%s:%s' % (local, host, remote) ] )
    #-- Whost.on_btnAdd_clicked }

    #-- Whost.on_btnDel_clicked {
    def on_btnDel_clicked(self, widget, *args):
        if self.treeTunel.get_selection().get_selected()[1]!=None:
            self.treeModel.remove(self.treeTunel.get_selection().get_selected()[1])
    #-- Whost.on_btnDel_clicked }

    #-- Whost.on_chkCommands_toggled {
    def on_chkCommands_toggled(self, widget, *args):
        self.txtCommands.set_sensitive(widget.get_active())
    #-- Whost.on_chkCommands_toggled }

    #-- Whost.on_btnBColor_clicked {
    def on_btnBColor_clicked(self, widget, *args):
        widget.selected_color = widget.get_color().to_string()
    #-- Whost.on_btnBColor_clicked }

    #-- Whost.on_chkDefaultColors_toggled {
    def on_chkDefaultColors_toggled(self, widget, *args):
        self.btnFColor.set_sensitive(not widget.get_active())
        self.btnBColor.set_sensitive(not widget.get_active())
    #-- Whost.on_chkDefaultColors_toggled }

    #-- Whost.on_btnFColor_clicked {
    def on_btnFColor_clicked(self, widget, *args):
        widget.selected_color = widget.get_color().to_string()
    #-- Whost.on_btnFColor_clicked }

    #-- Whost.on_btnBrowse_clicked {
    def on_btnBrowse_clicked(self, widget, *args):
        global wMain
        filename = show_open_dialog(parent=wMain.wMain, title=_("Abrir"), action=Gtk.FileChooserAction.OPEN)
        if filename != None:
            self.txtPrivateKey.set_text(filename)
    #-- Whost.on_btnBrowse_clicked }

class Wabout(SimpleGladeApp):

    def __init__(self, path="gnome-connection-manager.glade",
                 root="wAbout",
                 domain=domain_name, **kwargs):
        path = os.path.join(glade_dir, path)
        SimpleGladeApp.__init__(self, path, root, domain, parent=wMain.window)
        self.wAbout.set_icon_from_file(ICON_PATH)
    #-- Wabout.new {
    def new(self):       
        self.wAbout.set_program_name(app_name)
        self.wAbout.set_version(app_version)
        self.wAbout.set_website(app_web)    
    #-- Wabout.new }

    #-- Wabout custom methods {
    #   Write your own methods here
    #-- Wabout custom methods }

    #-- Wabout.on_wAbout_close {
    def on_wAbout_close(self, widget, *args):
        self.wAbout.destroy()
    #-- Wabout.on_wAbout_close }


class Wconfig(SimpleGladeApp):

    def __init__(self, path="gnome-connection-manager.glade",
                 root="wConfig",
                 domain=domain_name):
        path = os.path.join(glade_dir, path)
        SimpleGladeApp.__init__(self, path, root, domain, parent=wMain.window)

    #-- Wconfig.new {
    def new(self):        
        #Agregar controles
        self.tblGeneral = self.get_widget("tblGeneral")
        self.btnFColor = self.get_widget("btnFColor1")
        self.btnBColor = self.get_widget("btnBColor1")
        self.btnFont = self.get_widget("btnFont")
        self.lblFont = self.get_widget("lblFont")
        self.treeCmd = self.get_widget("treeCommands")
        self.treeCustom = self.get_widget("treeCustom")
        self.dlgColor = None
        self.capture_keys = False
        
        self.tblGeneral.rows = 0
        self.addParam(_("Separador de Palabras"), "conf.WORD_SEPARATORS", str)
        self.addParam(_(u"Tamaño del buffer"), "conf.BUFFER_LINES", int, 1, 1000000)
        self.addParam(_("Transparencia"), "conf.TRANSPARENCY", int, 0, 100)
        self.addParam(_("TERM"), "conf.TERM", str)
        self.addParam(_("Ruta de logs"), "conf.LOG_PATH", str)
        self.addParam(_("Abrir consola local al inicio"), "conf.STARTUP_LOCAL", bool)
        self.addParam(_("Log consola local"), "conf.LOG_LOCAL", bool)
        self.addParam(_(u"Pegar con botón derecho"), "conf.PASTE_ON_RIGHT_CLICK", bool)
        self.addParam(_(u"Copiar selección al portapapeles"), "conf.AUTO_COPY_SELECTION", bool)
        self.addParam(_("Confirmar al cerrar una consola"), "conf.CONFIRM_ON_CLOSE_TAB", bool)
        self.addParam(_(U"Confirmar al cerrar una consola con botón central del mouse"), "conf.CONFIRM_ON_CLOSE_TAB_MIDDLE", bool)
        self.addParam(_("Cerrar consola"), "conf.AUTO_CLOSE_TAB", list, [_("Nunca"), _("Siempre"), _(u"Sólo si no hay errores")])
        self.addParam(_("Confirmar al salir"), "conf.CONFIRM_ON_EXIT", bool)  
        self.addParam(_("Comprobar actualizaciones"), "conf.CHECK_UPDATES", bool)
        self.addParam(_(u"Ocultar botón donar"), "conf.HIDE_DONATE", bool)
        self.addParam(_(u"Título dinámico"), "conf.UPDATE_TITLE", bool)
        self.addParam(_(u"Título"), "conf.APP_TITLE", str)

        if len(conf.FONT_COLOR)==0:
            self.get_widget("chkDefaultColors1").set_active(True)
            self.btnFColor.set_sensitive(False)
            self.btnBColor.set_sensitive(False)
            fcolor=DEFAULT_FGCOLOR
            bcolor=DEFAULT_BGCOLOR
        else:
            self.get_widget("chkDefaultColors1").set_active(False)
            self.btnFColor.set_sensitive(True)
            self.btnBColor.set_sensitive(True)
            fcolor=conf.FONT_COLOR
            bcolor=conf.BACK_COLOR            
 
        self.btnFColor.set_color(parse_color(fcolor))
        self.btnBColor.set_color(parse_color(bcolor))
        self.btnFColor.selected_color=fcolor
        self.btnBColor.selected_color=bcolor
        
        #Fuente
        if len(conf.FONT)==0 or conf.FONT == 'monospace':
            conf.FONT = 'monospace'
        else:
            self.chkDefaultFont.set_active(False)
        self.btnFont.set_sensitive(not self.chkDefaultFont.get_active())
        self.btnFont.selected_font = Pango.FontDescription(conf.FONT)
        self.btnFont.set_label(self.btnFont.selected_font.to_string())
        self.btnFont.get_child().modify_font(self.btnFont.selected_font)
        
        #commandos
        self.treeModel = Gtk.TreeStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        self.treeCmd.set_model(self.treeModel)
        column = Gtk.TreeViewColumn(_(u"Acción"), Gtk.CellRendererText(), text=0)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_expand(True)
        self.treeCmd.append_column( column )
        
        renderer = Gtk.CellRendererText()
        renderer.set_property("editable", True)
        renderer.connect('edited', self.on_edited, self.treeModel, 1)
        renderer.connect('editing-started', self.on_editing_started, self.treeModel, 1)
        column = Gtk.TreeViewColumn(_("Atajo"), renderer, text=1)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)        
        self.treeCmd.append_column( column )
        
        self.treeModel2 = Gtk.TreeStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        self.treeCustom.set_model(self.treeModel2)
        renderer = MultilineCellRenderer()
        renderer.set_property("editable", True)
        renderer.connect('edited', self.on_edited, self.treeModel2, 0)
        column = Gtk.TreeViewColumn(_("Comando"), renderer, text=0)
        column.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        column.set_expand(True)       
        self.treeCustom.append_column( column )
        renderer = Gtk.CellRendererText()
        renderer.set_property("editable", True)
        renderer.connect('edited', self.on_edited, self.treeModel2, 1)
        renderer.connect('editing-started', self.on_editing_started, self.treeModel2, 1)        
        column = Gtk.TreeViewColumn(_("Atajo"), renderer, text=1)
        column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column.set_expand(False)        
        self.treeCustom.append_column( column )

        slist = sorted(shortcuts.items(), key=lambda i: i[1][0] )
        
        for s in slist:
            if type(s[1])==list:
                self.treeModel.append(None, [ s[1][0], s[0] ])
        for s in slist:
            if type(s[1])!=list:
                self.treeModel2.append(None, [ s[1], s[0] ])

        self.treeModel2.append(None, [ '', '' ])
    #-- Wconfig.new }

    #-- Wconfig custom methods {
    def addParam(self, name, field, ptype, *args):
        x = self.tblGeneral.rows
        self.tblGeneral.rows += 1
        value = eval(field)
        if ptype==bool:
            obj = Gtk.CheckButton()
            obj.set_label(name)
            obj.set_active(value)
            obj.set_alignment(0, 0.5)            
            obj.show()
            obj.field=field
            self.tblGeneral.attach(obj, 0, 2, x, x+1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, 0)            
        elif ptype==int:            
            obj = Gtk.SpinButton(climb_rate=10)
            if len(args)==2:
                obj.set_range(args[0], args[1])
            obj.set_increments(1, 10)
            obj.set_numeric(True)
            obj.set_value(value)                        
            obj.show()
            obj.field=field
            lbl = Gtk.Label(name)
            lbl.set_alignment(0, 0.5)
            lbl.show()
            self.tblGeneral.attach(lbl, 0, 1, x, x+1, Gtk.AttachOptions.FILL, 0)
            self.tblGeneral.attach(obj, 1, 2, x, x+1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, 0)
        elif ptype==list:
            obj = Gtk.ComboBoxText()
            for s in args[0]:
                obj.append_text(s)
            obj.set_active(value)
            obj.show()
            obj.field=field
            lbl = Gtk.Label(name)
            lbl.set_alignment(0, 0.5)
            lbl.show()
            self.tblGeneral.attach(lbl, 0, 1, x, x+1, Gtk.AttachOptions.FILL, 0)
            self.tblGeneral.attach(obj, 1, 2, x, x+1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, 0)
        else:            
            obj = Gtk.Entry()
            obj.set_text(value)            
            obj.show()
            obj.field=field
            lbl = Gtk.Label(name)
            lbl.set_alignment(0, 0.5)
            lbl.show()
            self.tblGeneral.attach(lbl, 0, 1, x, x+1, Gtk.AttachOptions.FILL, 0)
            self.tblGeneral.attach(obj, 1, 2, x, x+1, Gtk.AttachOptions.EXPAND|Gtk.AttachOptions.FILL, 0)
        
    def on_edited(self, widget, rownum, value, model, colnum):        
        model[rownum][colnum] = value
        if model==self.treeModel2:
            i = self.treeModel2.get_iter_first()
            while i != None:
                j = self.treeModel2.iter_next(i)
                self.treeModel2[i]
                if self.treeModel2[i][0] == self.treeModel2[i][1] == "":
                    self.treeModel2.remove(i)
                i = j
            self.treeModel2.append(None, [ '', '' ])
            if self.capture_keys:
                self.capture_keys = False                
            
    def on_editing_started(self, widget, entry, rownum, model, colnum):
        self.capture_keys = True
        entry.connect('key-press-event', self.on_treeCommands_key_press_event, model, rownum, colnum)        
    #-- Wconfig custom methods }

    #-- Wconfig.on_cancelbutton1_clicked {
    def on_cancelbutton1_clicked(self, widget, *args):
        self.get_widget("wConfig").destroy()
    #-- Wconfig.on_cancelbutton1_clicked }

    #-- Wconfig.on_okbutton1_clicked {
    def on_okbutton1_clicked(self, widget, *args):
        for obj in self.tblGeneral:
            if hasattr(obj, "field"):
                if isinstance(obj, Gtk.CheckButton):
                    value = obj.get_active()
                elif isinstance(obj, Gtk.SpinButton):
                    value = obj.get_value_as_int()
                elif isinstance(obj, Gtk.ComboBox):
                    value = obj.get_active()
                else:
                    value = '"%s"' % (obj.get_text())
                exec("%s=%s" % (obj.field, value))
        
        if self.get_widget("chkDefaultColors1").get_active():
            conf.FONT_COLOR=""
            conf.BACK_COLOR=""
        else:
            conf.FONT_COLOR = self.btnFColor.selected_color
            conf.BACK_COLOR = self.btnBColor.selected_color
        
        if self.btnFont.selected_font.to_string() != 'monospace' and not self.chkDefaultFont.get_active():
            conf.FONT = self.btnFont.selected_font.to_string()
        else:
            conf.FONT = ''
            
        #Guardar shortcuts
        scuts={}
        for x in self.treeModel:
            if x[0]!='' and x[1]!='':
                scuts[x[1]] = [x[0]]
        for x in self.treeModel2:
            if x[0]!='' and x[1]!='':
                scuts[x[1]] = x[0]        
        global shortcuts        
        shortcuts = scuts
        
        #Boton donate
        global wMain
        if conf.HIDE_DONATE:
            wMain.get_widget("btnDonate").hide()
        else:
            wMain.get_widget("btnDonate").show()
        
        #Recrear menu de comandos personalizados
        wMain.populateCommandsMenu()        
        wMain.writeConfig()
        
        self.get_widget("wConfig").destroy()
    #-- Wconfig.on_okbutton1_clicked }

    #-- Wconfig.on_btnBColor_clicked {
    def on_btnBColor_clicked(self, widget, *args):
        widget.selected_color = widget.get_color().to_string()
    #-- Wconfig.on_btnBColor_clicked }

    #-- Wconfig.on_btnFColor_clicked {
    def on_btnFColor_clicked(self, widget, *args):
        widget.selected_color = widget.get_color().to_string()
    #-- Wconfig.on_btnFColor_clicked }

    #-- Wconfig.on_chkDefaultColors_toggled {
    def on_chkDefaultColors_toggled(self, widget, *args):
        self.btnFColor.set_sensitive(not widget.get_active())
        self.btnBColor.set_sensitive(not widget.get_active())
    #-- Wconfig.on_chkDefaultColors_toggled }

    #-- Wconfig.on_chkDefaultFont_toggled {
    def on_chkDefaultFont_toggled(self, widget, *args):
        self.btnFont.set_sensitive(not widget.get_active())
        self.lblFont.set_sensitive(not widget.get_active())
    #-- Wconfig.on_chkDefaultFont_toggled }

    #-- Wconfig.on_btnFont_clicked {
    def on_btnFont_clicked(self, widget, *args):
        show_font_dialog(self, _("Seleccione la fuente"), self.btnFont)
    #-- Wconfig.on_btnFont_clicked }

    #-- Wconfig.on_treeCommands_key_press_event {
    def on_treeCommands_key_press_event(self, widget, event, *args):        
        if self.capture_keys and len(args)==3 and (event.keyval != Gdk.KEY_Return or
                                                   event.state != 0):
            model, rownum, colnum = args
            key = get_key_name(event)
            if key not in ['RETURN', 'KP_ENTER']:
                widget.set_text(get_key_name(event))
    #-- Wconfig.on_treeCommands_key_press_event }


class Wcluster(SimpleGladeApp):
    COLOR = parse_color('#FFFC00')
    
    def __init__(self, path="gnome-connection-manager.glade",
                 root="wCluster",
                 domain=domain_name, terms=None, **kwargs):
        self.terms = terms
        path = os.path.join(glade_dir, path)
        SimpleGladeApp.__init__(self, path, root, domain, parent=wMain.window)

    #-- Wcluster.new {
    def new(self):        
        self.treeHosts = self.get_widget('treeHosts')
        self.treeStore = Gtk.TreeStore( GObject.TYPE_BOOLEAN, GObject.TYPE_STRING, GObject.TYPE_OBJECT )
        for x in self.terms:
            self.treeStore.append( None, (False, x[0], x[1]) )
        self.treeHosts.set_model( self.treeStore )               
        
        crt = Gtk.CellRendererToggle()
        crt.set_property('activatable', True)
        crt.connect('toggled', self.on_active_toggled)        
        col = Gtk.TreeViewColumn(_("Activar"), crt, active=0)               
        self.treeHosts.append_column( col )
        self.treeHosts.append_column(Gtk.TreeViewColumn(_("Host"), Gtk.CellRendererText(), text=1 ))
        self.get_widget("txtCommands1").history = []
    #-- Wcluster.new }

    #-- Wcluster custom methods {
    #   Write your own methods here
    
    def on_active_toggled(self, widget, path):          
        self.treeStore[path][0] = not self.treeStore[path][0]
        self.change_color(self.treeStore[path][2], self.treeStore[path][0])                

    def change_color(self, term, activate):
        obj = term.get_parent()
        if obj == None:
            return
        nb = obj.get_parent()
        if nb == None:
            return
        if activate:
            nb.get_tab_label(obj).change_color(Wcluster.COLOR)
        else:
            nb.get_tab_label(obj).restore_color()
            
    #-- Wcluster custom methods }

    #-- Wcluster.on_wCluster_destroy {
    def on_wCluster_destroy(self, widget, *args):
        self.on_btnNone_clicked(None)
    #-- Wcluster.on_wCluster_destroy }

    #-- Wcluster.on_cancelbutton2_clicked {
    def on_cancelbutton2_clicked(self, widget, *args):
        self.get_widget("wCluster").destroy()
    #-- Wcluster.on_cancelbutton2_clicked }

    #-- Wcluster.on_btnAll_clicked {
    def on_btnAll_clicked(self, widget, *args):
        for x in self.treeStore:
            x[0] = True
            self.change_color(x[2], x[0])
    #-- Wcluster.on_btnAll_clicked }

    #-- Wcluster.on_btnNone_clicked {
    def on_btnNone_clicked(self, widget, *args):
        for x in self.treeStore:
            x[0] = False
            self.change_color(x[2], x[0])
    #-- Wcluster.on_btnNone_clicked }

    #-- Wcluster.on_btnInvert_clicked {
    def on_btnInvert_clicked(self, widget, *args):
        for x in self.treeStore:
            x[0] = not x[0]
            self.change_color(x[2], x[0])
    #-- Wcluster.on_btnInvert_clicked }

    #-- Wcluster.on_txtCommands_key_press_event {
    def on_txtCommands_key_press_event(self, widget, event, *args):   
        if not event.state & Gdk.ModifierType.CONTROL_MASK and Gdk.keyval_name(event.keyval).upper() == 'RETURN':           
           buf = widget.get_buffer()
           text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
           buf.set_text('')
           for x in self.treeStore:
               if x[0]:
                   vte_feed(x[2], text + '\r')
           widget.history.append(text)
           widget.history_index = -1
           return True
        if event.state & Gdk.ModifierType.CONTROL_MASK and Gdk.keyval_name(event.keyval).upper() in ['UP','DOWN']:
            if len(widget.history) > 0:
                if Gdk.keyval_name(event.keyval).upper() == 'UP':
                    widget.history_index -= 1
                    if widget.history_index < -1:
                        widget.history_index = len(widget.history) - 1
                else:
                    widget.history_index += 1
                    if widget.history_index >= len(widget.history):
                        widget.history_index = -1                        
                widget.get_buffer().set_text(widget.history[widget.history_index] if widget.history_index>=0 else '')
    #-- Wcluster.on_txtCommands_key_press_event }


class NotebookTabLabel(Gtk.HBox):
    '''Notebook tab label with close button.
    '''
    def __init__(self, title, owner_, widget_, popup_):
        Gtk.HBox.__init__(self, homogeneous=False, spacing=0)
        
        self.title = title
        self.owner = owner_
        self.eb = Gtk.EventBox()
        label = self.label = Gtk.Label()
        self.eb.connect('button-press-event', self.popupmenu, label)
        label.halign=0
        label.valign=0.5
        label.set_text(title)
        self.eb.add(label)        
        self.pack_start(self.eb, True, True, 0)        
        label.show()        
        self.eb.show()                
        close_image = Gtk.Image.new_from_icon_name(Gtk.STOCK_CLOSE, Gtk.IconSize.MENU)
        b, image_w, image_h = Gtk.icon_size_lookup(Gtk.IconSize.MENU)
        self.widget_=widget_
        self.popup = popup_        
        close_btn = Gtk.Button()
        close_btn.set_relief(Gtk.ReliefStyle.NONE)
        close_btn.connect('clicked', self.on_close_tab, owner_)
        close_btn.set_size_request(image_w+7, image_h+6)
        close_btn.add(close_image)
        #style = close_btn.get_style();
        self.eb2 = Gtk.EventBox()
        self.eb2.add(close_btn)        
        self.pack_start(self.eb2, False, False, 0)
        self.eb2.show()
        close_btn.show_all()  
        self.is_active = True
        self.eb.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK) #let the scroll-event pass through
        self.show()
        
    def change_color(self, color):
        self.bg_active = self.eb.get_style_context().get_background_color(Gtk.StateFlags.ACTIVE)
        self.bg_normal = self.eb.get_style_context().get_background_color(Gtk.StateFlags.NORMAL)
        self.eb.modify_bg(Gtk.StateType.ACTIVE, color)
        self.eb2.modify_bg(Gtk.StateType.ACTIVE, color)
        self.eb.modify_bg(Gtk.StateType.NORMAL, color)
        self.eb2.modify_bg(Gtk.StateType.NORMAL, color)
        
    def restore_color(self):
        if hasattr(self, 'bg_active'):
            self.eb.override_background_color(Gtk.StateFlags.ACTIVE, self.bg_active)
            self.eb2.override_background_color(Gtk.StateFlags.ACTIVE, self.bg_active)
            self.eb.override_background_color(Gtk.StateFlags.NORMAL, self.bg_normal)
            self.eb2.override_background_color(Gtk.StateFlags.NORMAL, self.bg_normal)
        
    def on_close_tab(self, widget, notebook, *args):
        if conf.CONFIRM_ON_CLOSE_TAB and msgconfirm("%s [%s]?" % ( _("Cerrar consola"), self.label.get_text().strip()) ) != Gtk.ResponseType.OK:
            return True
        
        self.close_tab(widget)

    def close_tab(self, widget):
        notebook = self.widget_.get_parent()        
        page=notebook.page_num(self.widget_)
        if page >= 0:
            notebook.is_closed = True
            notebook.remove_page(page)
            notebook.is_closed = False       
            self.widget_.destroy()
        
    def mark_tab_as_closed(self):
        self.label.set_markup("<span color='darkgray' strikethrough='true'>%s</span>" % (self.label.get_text()))
        self.is_active = False
        if conf.AUTO_CLOSE_TAB != 0:
            if conf.AUTO_CLOSE_TAB == 2:
                terminal = self.widget_.get_parent().get_nth_page(self.widget_.get_parent().page_num(self.widget_)).get_child()
                if terminal.get_child_exit_status() != 0:
                    return
            self.close_tab(self.widget_)
            
    def mark_tab_as_active(self):
        self.label.set_markup("%s" % (self.label.get_text()))
        self.is_active = True
        
    def get_text(self):
        return self.label.get_text()

    def popupmenu(self, widget, event, label):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:    
            self.popup.label = self.label
            if self.is_active:
                self.popup.mnuReopen.hide()
            else:
                self.popup.mnuReopen.show()
            
            #enable or disable log checkbox according to terminal 
            self.popup.mnuLog.set_active( hasattr(self.widget_.get_child(), "log_handler_id") and self.widget_.get_child().log_handler_id != 0 )
            self.popup.popup( None, None, None, None, event.button, event.time)
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 2:
            if conf.CONFIRM_ON_CLOSE_TAB_MIDDLE and msgconfirm("%s [%s]?" % ( _("Cerrar consola"), self.label.get_text().strip()) ) != Gtk.ResponseType.OK:
                return True          
            self.close_tab(self.widget_)

class EntryDialog( Gtk.Dialog):
    def __init__(self, title, message, default_text='', modal=True, mask=False):
        Gtk.Dialog.__init__(self)
        self.set_title(title)
        self.connect("destroy", self.quit)
        self.connect("delete_event", self.quit)
        if modal:
            self.set_modal(True)
        box = Gtk.VBox(spacing=10)
        box.set_border_width(10)
        self.vbox.pack_start(box, True, True, 0)
        box.show()
        if message:
            label = Gtk.Label(message)
            box.pack_start(label, True, True, 0)
            label.show()
        self.entry = Gtk.Entry()
        self.entry.set_text(default_text)
        self.entry.set_visibility(not mask)
        box.pack_start(self.entry, True, True, 0)
        self.entry.show()
        self.entry.grab_focus()
        button = Gtk.Button(stock=Gtk.STOCK_OK)
        button.connect("clicked", self.click)
        self.entry.connect("activate", self.click)
        button.set_can_default(True)
        self.action_area.pack_start(button, True, True, 0)
        button.show()
        button.grab_default()
        button = Gtk.Button(stock=Gtk.STOCK_CANCEL)
        button.connect("clicked", self.quit)
        button.set_can_default(True)
        self.action_area.pack_start(button, True, True, 0)
        button.show()
        self.ret = None

    def quit(self, w=None, event=None):
        self.hide()
        self.destroy()        

    def click(self, button):
        self.value = self.entry.get_text()        
        self.response(Gtk.ResponseType.OK)



class CellTextView(Gtk.TextView, Gtk.CellEditable):

    __gtype_name__ = "CellTextView"

    __gproperties__ = {
            'editing-canceled': (bool, 'Editing cancelled', 'Editing was cancelled', False, GObject.ParamFlags.READWRITE),
        }
        
    def do_editing_done(self, *args):
        self.remove_widget()

    def do_remove_widget(self, *args):
        pass

    def do_start_editing(self, *args):
        pass

    def get_text(self):
        text_buffer = self.get_buffer()
        bounds = text_buffer.get_bounds()
        return text_buffer.get_text(*bounds, True)

    def set_text(self, text):
        self.get_buffer().set_text(text)


class MultilineCellRenderer(Gtk.CellRendererText):

    __gtype_name__ = "MultilineCellRenderer"

    def __init__(self):
        Gtk.CellRendererText.__init__(self)
        self._in_editor_menu = False

    def _on_editor_focus_out_event(self, editor, *args):
        if self._in_editor_menu: return
        editor.remove_widget()
        self.emit("editing-canceled")

    def _on_editor_key_press_event(self, editor, event):
        if event.state & (Gdk.ModifierType.SHIFT_MASK | Gdk.ModifierType.CONTROL_MASK): return
        if event.keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            editor.remove_widget()
            self.emit("edited", editor.path, editor.get_text())
        elif event.keyval == Gdk.KEY_Escape:
            editor.remove_widget()
            self.emit("editing-canceled")

    def _on_editor_populate_popup(self, editor, menu):
        self._in_editor_menu = True
        def on_menu_unmap(menu, self):
            self._in_editor_menu = False
        menu.connect("unmap", on_menu_unmap, self)

    def _on_editor_pressed(self, editor, menu):
        #avoid bug: gtk_text_mark_get_buffer: assertion 'GTK_IS_TEXT_MARK (mark)' failed        
        return True

    def do_start_editing(self, event, widget, path, bg_area, cell_area, flags):
        editor = CellTextView()
        editor.modify_font(self.props.font_desc)
        editor.set_text(self.props.text)
        editor.set_size_request(cell_area.width, cell_area.height)
        editor.set_border_width(min(self.props.xpad, self.props.ypad))
        editor.path = path
        editor.connect("focus-out-event", self._on_editor_focus_out_event)
        editor.connect("key-press-event", self._on_editor_key_press_event)
        editor.connect("populate-popup", self._on_editor_populate_popup)
        editor.connect("button-press-event", self._on_editor_pressed)
        editor.show()
        return editor


from threading import Thread

class CheckUpdates(Thread):
    
    def __init__(self, p):
        Thread.__init__(self)
        self.parent = p
        
    def msg(self, text, parent):  
        self.msgBox = Gtk.MessageDialog(parent=parent, modal=True, message_type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK, text=text)
        self.msgBox.set_icon_from_file(ICON_PATH)
        self.msgBox.connect('response', self.on_clicked)
        self.msgBox.show_all()      
        return False
        
    def on_clicked(self, *args):
        self.msgBox.destroy()
    
    def run(self):
        try:
            import urllib.request as urllib, socket        
            socket.setdefaulttimeout(5)
            web = urllib.urlopen('http://kuthulu.com/gcm/_current.html')
            if web.getcode()==200:
                new_version = web.readline().strip().decode('utf-8')
                if len(new_version)>0 and new_version > app_version:                                
                    self.tag = GLib.timeout_add(0, self.msg, "%s\n\nCURRENT VERSION: %s\nNEW VERSION: %s" % (_("Hay una nueva version disponible en http://kuthulu.com/gcm/?module=download"), app_version, new_version), self.parent.get_widget("wMain"))
        except Exception as e:            
            pass


def main():
    w_main = Wmain()
    w_main.run()


if __name__ == "__main__":
    main()
