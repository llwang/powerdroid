#!/usr/bin/python2.4
# -*- coding: us-ascii -*-
# vim:ts=2:sw=2:softtabstop=0:tw=74:smarttab:expandtab
#
# Copyright The Android Open Source Project

"""CLI commands for test sets.
"""


from pycopia import timelib
from pycopia import CLI

from droid.instruments import gpibCLI
from droid.instruments import core


class Ag8960CLI(gpibCLI.GenericInstrument):

  def _reset_scopes(self):
    super(Ag8960CLI, self)._reset_scopes()
    self.add_completion_scope("downlinkaudio", ["off", "none", "echo", 
        "silence", "random", "sin300", "sin1000", "sin3000", "multitone"])
    self.add_completion_scope("profile", 
        ["gsm", "grps", "egprs", "edge", "edgehp"])
    self.add_completion_scope("use", 
        ["afgenerator", "afanalyzer", "mtgenerator", "mtanalyzer", "srbber",
          "mstxpower", "msetxpower"])

  def use(self, argv):
    """use afgen | afana | mtgen | mtana | srbber | mstxpower | msetxpower
  Select a subinstrument to use.
    """
    devname = argv[1]
    if devname.startswith("afg"):
      inst = self._obj.GetAudioGenerator()
      cmd = self.clone(Ag8960_AFG_CLI)
    elif devname.startswith("afa"):
      inst = self._obj.GetAudioAnalyzer()
      cmd = self.clone(Ag8960_AFA_CLI)
    elif devname.startswith("mtg"):
      inst = self._obj.GetMultitoneAudioGenerator()
      cmd = self.clone(Ag8960_MTG_CLI)
    elif devname.startswith("mta"):
      inst = self._obj.GetMultitoneAudioAnalyzer()
      cmd = self.clone(Ag8960_MTA_CLI)
    elif devname.startswith("srb"):
      inst = self._obj.GetEGPRSBitErrorMeasurer()
      cmd = self.clone(SRBberCLI)
    elif devname.startswith("mst"):
      inst = self._obj.GetTransmitPowerMeasurer()
      cmd = self.clone(MeasurerCLI)
    elif devname.startswith("mse"):
      inst = self._obj.GetEGPRSTransmitPowerMeasurer()
      cmd = self.clone(MeasurerCLI)
    elif devname.startswith("thr"):
      inst = self._obj.GetDataThroughputMeasurer()
      cmd = self.clone(ThroughputCLI)
    else:
      raise CLI.CLISyntaxError
    errs = inst.Errors()
    if errs:
      self._print("Pre-existing errors:")
      for err in errs:
        self._print("  ", err)
    cmd._setup(inst, "%%I%s%%N(%s)> " % (self._obj._configname, inst.__class__.__name__))
    raise CLI.NewCommand, cmd

  def application(self, argv):
    """application -l [<newname>]
  Get, set, or list available applications."""
    opts, longopts, args = self.getopt(argv, "l")
    for opt, arg in opts:
      if opt == "-l":
        self._print_list(self._obj.GetApplicationList())
        return
    if len(args) > 0:
        errors = self._obj.SetApplication(args[0])
        if errors:
          self._print_list(errors)
        else:
          self._print("Application set.")
    else:
      self._print(self._obj.GetCurrentApplication())

  def ping(self, argv):
    """ping [-c <count>] [-s <size>] [-t <timeout>] [target]
  Perform an ICMP ping from the test set. 
  target is an IP address, defaults to DUT if not provided."""
    target = None
    count = 5
    size = 128
    timeout = 3
    opts, longopts, args = self.getopt(argv, "c:s:t:")
    if args:
      target = args[0]
    for opt, optarg in opts:
      if opt == "-c":
        count = int(optarg)
      elif opt == "-s":
        size = int(optarg)
      elif opt == "-t":
        timeout = int(optarg)
    report = self._obj.Ping(target, count, size, timeout)
    self._print(report)
    return report

  def dial(self, argv):
    """dial [originating_number]
  Initiate a call."""
    if len(argv) > 1:
      orig = argv[1]
    else:
      orig = None
    self._obj.Call(orig)

  def hangup(self, argv):
    """hangup
  Hang up an active call."""
    self._obj.Hangup()

  def active(self, argv):
    """active
  Is a call currently active?"""
    if self._obj.IsCallActive():
      self._print("Call is active.")
    else:
      self._print("Call is NOT active.")

  def traffic(self, argv):
    """traffic
  Report the IP traffic counters. First time stores counters. Subsequent
  times also report delta and average rate."""
    rpt = self._obj.GetIPCounters()
    timestamp = timelib.now()
    self._print(rpt)
    try:
      oldrpt = self._ip_traffic_report
    except AttributeError:
      pass
    else:
      self._print("\nDelta:")
      diff = rpt - oldrpt
      self._print(diff)
      self._print("\nRate (per sec):")
      self._print(diff / (timestamp - oldrpt.timestamp))
    rpt.timestamp = timestamp
    self._ip_traffic_report = rpt

  def downlinkaudio(self, argv):
    """downlinkaudio [<mode>]
  Set the downlink (to DUT) audio speech source. 
  Mode is one of:
    none
    echo
    sid  (or silence)
    prbs15 (or random)
    sin300
    sin1000
    sin3000
    multitone

  If mode is omitted then report current mode.
    """
    if len(argv) > 1:
      audiomode = argv[1]
      if audiomode.startswith("ra"):
        audiomode = "PRBS15"
      elif audiomode.startswith("si"):
        audiomode = "SID"
      elif audiomode.startswith("mu"):
        audiomode = "MULTITONE"
      self._obj.SetDownlinkAudio(audiomode)
    else:
      mode = self._obj.GetDownlinkAudio()
      self._print(mode)
      return mode

  def wipescreen(self, argv):
    """wipescreen
  Remove error messages from screen."""
    self._obj.ClearScreen()

  def distance(self, argv):
    """distance <relative_distance>
  Set the relative distance (simulated) of the mobile and base station.
  Values such as "near", "far", "normal" are acceptable."""
    self._obj.SetDistance(argv[1])


class Ag8960GPRSCLI(Ag8960CLI):

  def _reset_scopes(self):
    super(Ag8960GPRSCLI, self)._reset_scopes()
    self.add_completion_scope("toggle", ["qosp",])

  def profile(self, argv):
    """profile (gsm | grps | egprs | edge | edge_far | edgehp) [<network>]
  Set the carrier profile."""
    name = argv[1]
    if len(argv) > 2:
      network = argv[2]
    else:
      network = self._environ["SIM"]
    self._obj.SetProfile(name, network)

  def detach(self, argv):
    """detach
  Initiate a GPRS detach."""
    self._obj.Detach()

  def data(self, argv):
    """data on | off
  Set the data connection state."""
    val = core.GetBoolean(argv[1])
    self._obj.DataConnection(val)

  def qosp(self, argv):
    """qosp [<qospN>] [<ipindex>]
  Get or set the quality of service profile."""
    if len(argv) > 1:
      if len(argv) > 2:
        ipindex = int(argv[2])
      else:
        ipindex = 1
      qosp = int(argv[1])
      self._obj.SetMSQualityOfService(qosp, ipindex)
    else:
      self._print(self._obj.GetMSQualityOfService())

  def toggle(self, argv):
    """toggle <setting>
  Toggle the setting, by name.
  Currently available:
    qosp - quality of service profile
    data - data state
  """
    setting = argv[1]
    if setting.startswith("qo"):
      if len(argv) > 2:
        ipindex = int(argv[2])
      else:
        ipindex = 1
      self._ToggleQOS(ipindex)
    elif setting.startswith("da"):
      self._ToggleData()
    else:
      self._ui.error("No such setting value.")

  def _ToggleQOS(self, ipindex):
      qosp = self._obj.GetMSQualityOfService(ipindex)
      if qosp != 1:
        qosp = 1
      else:
        qosp = 2
      self._obj.SetMSQualityOfService(qosp, ipindex)

  def _ToggleData(self):
    try:
      self._datastate = not self._datastate
    except AttributeError:
      self._datastate = False
    self._obj.DataConnection(self._datastate)

  def multislot(self, argv):
    """multislot [<downlink> [<uplink>]]
  Get or set multislot configuration."""
    if len(argv) > 1:
      if len(argv) > 2:
        uplink = int(argv[2])
      else:
        uplink = 2
      downlink = int(argv[1])
      self._obj.SetMultiSlotConfig(downlink, uplink)
    else:
      downlinks, uplinks = self._obj.GetMultiSlotConfig()
      self._print("downlinks: %d, uplinks: %d" % (downlinks, uplinks))
      self._print("(%dD%dU)" % (downlinks, uplinks))


class Ag8960CDMACLI(Ag8960CLI):

  def profile(self, argv):
    """profile cdma
  Set the carrier profile."""
    name = argv[1]
    self._obj.SetProfile(name, "test") # authentication required


def ParseBTAddress(btstring):
  if btstring.find(":") > 0:
    addr = 0
    parts = [int(s, 16) for s in btstring.split(":")]
    parts.reverse() # LSB now first
    for place, value in enumerate(parts):
      addr += value * (256 ** place)
    return addr
  else:
    return eval(btstring) # eval allows decimal or hex style values


class N4010aCLI(gpibCLI.GenericInstrument):

  def _reset_scopes(self):
    super(N4010aCLI, self)._reset_scopes()
    self.add_completion_scope("use", ["afgenerator", "afanalyzer"])

  def use(self, argv):
    """use afgen | afana
  Select a subinstrument to use.
    """
    devname = argv[1]
    if devname.startswith("afg"):
      inst = self._obj.GetAudioGenerator()
      cmd = self.clone(N4010aAudioGeneratorCLI)
    elif devname.startswith("afa"):
      inst = self._obj.GetAudioAnalyzer()
      cmd = self.clone(N4010aAudioAnalyzerCLI)
    else:
      raise CLI.CLISyntaxError
    errs = inst.Errors()
    if errs:
      self._print("Pre-existing errors:")
      for err in errs:
        self._print("  ", err)
    cmd._setup(inst, "%%I%s%%N(%s)> " % (self._obj._configname, inst.__class__.__name__))
    raise CLI.NewCommand, cmd

  def discover(self, argv):
    """discover [<timeout>]
  Discover and print information about bluetooth devices in the area.
  Optional timeout value may be supplied."""
    if len(argv) > 1:
      timeout = float(argv[1])
    else:
      timeout = None # use default
    devlist = self._obj.Discover(timeout)
    self._print("Devices:")
    for dev in devlist:
      self._print(dev)

  def headset(self, argv):
    """headset <btaddress>
    Activate the headset profile to pair with <btaddress>."""
    addr = ParseBTAddress(argv[1])
    self._obj.SetupHeadsetProfile()
    self._obj.ActivateHeadsetProfile(addr)
    pin = self._obj.GetDUTPIN()
    self._print(
        "Perform pairing operation on handset now, if not already done.")
    self._print("Use pin: %r" % pin)

  def activaterole(self, argv):
    """activaterole
  Activate set role."""
    self._obj.ActivateRole()

  def deactivaterole(self, argv):
    """deactivaterole
  Deactivate set role."""
    self._obj.DeactivateRole()

  def condition(self, argv):
    """condition
  Print operational condition."""
    for cond in self._obj.GetAllQuestionable():
      self._print(cond)
    for cond in self._obj.GetAllOperCondition():
      self._print(cond)

  def hangup(self, argv):
    """hangup
  Hang up an active call."""
    self._obj.Hangup()

  def answer(self, argv):
    """answer
  Answer an alerting call from headset."""
    self._obj.Answer()

  def isactive(self, argv):
    """isactive
  Is a call currently active?"""
    if self._obj.IsCallActive():
      self._print("Call is active.")
    else:
      self._print("Call is NOT active.")


class GeneratorCLI(gpibCLI.GenericInstrument):
  pass


class AnalyzerCLI(gpibCLI.GenericInstrument):

  def prepare(self, argv):
    """prepare
  Prepare the instrument for testing using the current environment."""
    self._obj.Prepare(self._environ)

  def perform(self, argv):
    """perform
  Run the measurement."""
    disp = self._obj.Perform()
    if disp:
      self._print(" Frequency: %s" % self._obj.GetFrequency())
      self._print("   Voltage: %s" % self._obj.GetVoltage())
      self._print("Distortion: %s %%" % self._obj.GetDistortion())
      self._print("     SINAD: %s dB" % self._obj.GetSINAD())
    else:
      self._print(disp)

  def measure(self, argv):
    """measure
  Start a measurement and report results."""
    self.prepare(argv)
    self.perform(argv)


class MeasurerCLI(gpibCLI.GenericInstrument):

  def prepare(self, argv):
    """prepare
  Prepare the instrument for testing using the current environment."""
    self._obj.Prepare(self._environ)

  def perform(self, argv):
    """perform
  Run the measurement."""
    rpt = self._obj.Perform()
    self._print(str(rpt))
    return rpt

  def measure(self, argv):
    """measure
  Start a measurement and report results."""
    rv = self._obj.Measure(self._environ)
    self._print(str(rv))
    return rv

  def finish(self, argv):
    """finish
  Finish with the measurer, which should clean up its state."""
    self._obj.Finish()
    raise CLI.CommandQuit


class N4010aAudioGeneratorCLI(GeneratorCLI):
  pass


class N4010aAudioAnalyzerCLI(AnalyzerCLI):

  # don't call superclass for this one, it breaks.
  def _reset_scopes(self):
    pass


class SRBberCLI(MeasurerCLI):

  def startdata(self, argv):
    """startdata
  Kick off the data connection."""
    self._obj.StartData()


class ThroughputCLI(MeasurerCLI):

  def _reset_scopes(self):
    super(ThroughputCLI, self)._reset_scopes()
    self.add_completion_scope("throughput", ["iprx", "iptx", "otarx", "otatx"])

  def throughput(self, argv):
    """throughput iprx | iptx | otarx | otatx
  Show the current values for the specified network trace measurement."""
    trace = argv[1]
    self._print(self._obj.GetDataRate(trace.upper()))

  def clear(self, argv):
    """clear
  Reset counters."""
    self._obj.Clear()


class Ag8960_AFG_CLI(GeneratorCLI):
  pass


class Ag8960_AFA_CLI(AnalyzerCLI):
  def _reset_scopes(self):
    super(Ag8960_AFA_CLI, self)._reset_scopes()
    self.add_completion_scope("filter_type", 
        ["none", "tbp", "cmes", "bpas50", "bpas300"])


class Ag8960_MTG_CLI(GeneratorCLI):
  pass


class Ag8960_MTA_CLI(AnalyzerCLI):
  pass



