import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import time
import json

class SignalGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ESP32 Signal Generator Control")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Serial connection
        self.serial_port = None
        self.connected = False
        self.connect_lock = threading.Lock()
        
        # Signal parameters
        self.signal_types = ["Sine", "Square", "Triangle"]
        self.modulation_types = ["MFSK", "MPSK", "ASK", "SWEEP", "PWM", "AM"]
        
        # Create GUI
        self.create_widgets()
        
        # Update port list on startup
        self.update_port_list()
        
    def validate_float(self, P):
        """Validation function for float entries"""
        if P.strip() == "":
            return True
        try:
            float(P)
            return True
        except ValueError:
            return False
    
    def validate_int(self, P):
        """Validation function for integer entries"""
        if P.strip() == "":
            return True
        try:
            int(P)
            return True
        except ValueError:
            return False
        
    def create_widgets(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Connection Frame
        conn_frame = ttk.LabelFrame(main_frame, text="Connection", padding="10")
        conn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Port selection
        ttk.Label(conn_frame, text="Port:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.port_combobox = ttk.Combobox(conn_frame, width=30)
        self.port_combobox.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Refresh and connect buttons
        ttk.Button(conn_frame, text="Refresh", command=self.update_port_list).grid(row=0, column=2, padx=5, pady=5)
        self.connect_button = ttk.Button(conn_frame, text="Connect", command=self.toggle_connection)
        self.connect_button.grid(row=0, column=3, padx=5, pady=5)
        
        # Status label
        self.status_label = ttk.Label(conn_frame, text="Status: Disconnected", foreground="red")
        self.status_label.grid(row=0, column=4, sticky=tk.W, padx=5, pady=5)
        
        # Channels Frame
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs for each channel
        self.create_channel_tab(1)
        self.create_channel_tab(2)
        self.create_modulation_tab()
        
        # Track the active tab for enabling/disabling channels
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        
        # Bottom frame for global controls
        bottom_frame = ttk.Frame(main_frame, padding="10")
        bottom_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Apply settings button
        ttk.Button(bottom_frame, text="Apply All Settings", command=self.apply_all_settings).pack(side=tk.RIGHT, padx=5)
        
    def create_channel_tab(self, channel_num):
        channel_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(channel_frame, text=f"Channel {channel_num}")
        
        # Signal parameters
        param_frame = ttk.LabelFrame(channel_frame, text="Signal Parameters", padding="10")
        param_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Signal Type
        ttk.Label(param_frame, text="Signal Type:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        signal_type = tk.StringVar(value=self.signal_types[0])
        signal_type_combobox = ttk.Combobox(param_frame, textvariable=signal_type, values=self.signal_types, state="readonly")
        signal_type_combobox.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Frequency
        ttk.Label(param_frame, text="Frequency (Hz):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        frequency = tk.DoubleVar(value=1000.0)
        vcmd = (self.root.register(self.validate_float), '%P')
        frequency_entry = ttk.Entry(param_frame, textvariable=frequency, width=15, validate='key', validatecommand=vcmd)
        frequency_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        freq_scale = ttk.Scale(param_frame, from_=1, to=3000000, orient=tk.HORIZONTAL, 
                              variable=frequency, length=200)
        freq_scale.grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Phase (-180 to 180 degrees)
        ttk.Label(param_frame, text="Phase (degrees):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        phase = tk.DoubleVar(value=0.0)
        phase_entry = ttk.Entry(param_frame, textvariable=phase, width=15, validate='key', validatecommand=vcmd)
        phase_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        phase_scale = ttk.Scale(param_frame, from_=-180, to=180, orient=tk.HORIZONTAL, 
                              variable=phase, length=200)
        phase_scale.grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)
        
        # Enable/Disable channel
        enabled = tk.BooleanVar(value=True)
        channel_enabled_check = ttk.Checkbutton(param_frame, text="Enable Channel", variable=enabled)
        channel_enabled_check.grid(row=3, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Apply button for this channel
        # ttk.Button(param_frame, text="Apply", command=lambda: self.apply_channel_settings(
        #     channel_num, signal_type.get(), frequency.get(), phase.get(), enabled.get()
        # )).grid(row=3, column=2, sticky=tk.E, padx=5, pady=5)
        
        # Store the variables for this channel
        setattr(self, f"channel_{channel_num}_type", signal_type)
        setattr(self, f"channel_{channel_num}_freq", frequency)
        setattr(self, f"channel_{channel_num}_phase", phase)
        setattr(self, f"channel_{channel_num}_enabled", enabled)
        setattr(self, f"channel_{channel_num}_enabled_check", channel_enabled_check)
    
    def create_modulation_tab(self):
        mod_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(mod_frame, text="Modulation")
        
        # Modulation parameters
        param_frame = ttk.LabelFrame(mod_frame, text="Modulation Parameters", padding="10")
        param_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Modulation Type
        ttk.Label(param_frame, text="Modulation Type:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        mod_type = tk.StringVar(value=self.modulation_types[0])
        mod_type_combobox = ttk.Combobox(param_frame, textvariable=mod_type, values=self.modulation_types, state="readonly")
        mod_type_combobox.grid(row=0, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)

        # M parameter (between modulation type and carrier frequency)
        ttk.Label(param_frame, text="M (states/symbols):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        mod_m = tk.IntVar(value=2)
        vcmd_int = (self.root.register(self.validate_int), '%P')
        mod_m_entry = ttk.Entry(param_frame, textvariable=mod_m, width=15, validate='key', validatecommand=vcmd_int)
        mod_m_entry.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Modulation frequency
        ttk.Label(param_frame, text="Carrier Frequency (Hz):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        mod_freq = tk.DoubleVar(value=100000.0)
        vcmd = (self.root.register(self.validate_float), '%P')
        mod_freq_entry = ttk.Entry(param_frame, textvariable=mod_freq, width=15, validate='key', validatecommand=vcmd)
        mod_freq_entry.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Delta Frequency (replacing Min/Max Frequency)
        ttk.Label(param_frame, text="Delta (Hz/degrees):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        delta_freq = tk.DoubleVar(value=1000.0)
        delta_freq_entry = ttk.Entry(param_frame, textvariable=delta_freq, width=15, validate='key', validatecommand=vcmd)
        delta_freq_entry.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Baud Rate
        ttk.Label(param_frame, text="Baud Rate (Hz) / Fm:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        baud_rate = tk.DoubleVar(value=1000.0)  # Changed from IntVar to DoubleVar
        baud_rate_entry = ttk.Entry(param_frame, textvariable=baud_rate, width=15, validate='key', validatecommand=vcmd)
        baud_rate_entry.grid(row=4, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Modulation Time (for SWEEP)
        ttk.Label(param_frame, text="Modulation Time (s):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        mod_time = tk.DoubleVar(value=10.0)
        mod_time_entry = ttk.Entry(param_frame, textvariable=mod_time, width=15, validate='key', validatecommand=vcmd)
        mod_time_entry.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Data input (for digital modulation)
        ttk.Label(param_frame, text="Data (Ex: 255,74,56,122,... ):").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        data_string = tk.StringVar(value="")
        data_entry = ttk.Entry(param_frame, textvariable=data_string, width=40)
        data_entry.grid(row=6, column=1, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Enable/Disable modulation
        mod_enabled = tk.BooleanVar(value=False)
        ttk.Checkbutton(param_frame, text="Enable Modulation", variable=mod_enabled, 
                      command=lambda: self.toggle_modulation(mod_enabled.get())).grid(row=7, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # Apply button for modulation
        # ttk.Button(param_frame, text="Apply Modulation", command=lambda: self.apply_modulation_settings(
        #     mod_type.get(), mod_m.get(), mod_freq.get(), delta_freq.get(), baud_rate.get(), mod_time.get(), data_string.get(), mod_enabled.get()
        # )).grid(row=7, column=2, sticky=tk.E, padx=5, pady=5)
        
        # Store modulation variables
        self.modulation_type = mod_type
        self.modulation_m = mod_m
        self.modulation_freq = mod_freq
        self.modulation_delta_freq = delta_freq  # Changed from min_max_freq
        self.modulation_baud_rate = baud_rate
        self.modulation_time = mod_time
        self.modulation_data = data_string
        self.modulation_enabled = mod_enabled
    
    def toggle_modulation(self, enabled):
        """Enable or disable regular channels based on modulation state"""
        if enabled:
            # Disable regular channels when modulation is enabled
            self.channel_1_enabled.set(False)
            self.channel_2_enabled.set(False)
            self.channel_1_enabled_check.state(['disabled'])
            self.channel_2_enabled_check.state(['disabled'])
        else:
            # Enable regular channels when modulation is disabled
            self.channel_1_enabled_check.state(['!disabled'])
            self.channel_2_enabled_check.state(['!disabled'])
    
    def on_tab_change(self, event):
        """Handle tab change events to update the UI state"""
        selected_tab = self.notebook.index("current")
        if selected_tab == 2:  # Modulation tab
            if self.modulation_enabled.get():
                self.channel_1_enabled.set(False)
                self.channel_2_enabled.set(False)
                self.channel_1_enabled_check.state(['disabled'])
                self.channel_2_enabled_check.state(['disabled'])
    
    def update_port_list(self):
        """Update the list of available serial ports"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox['values'] = ports
        if ports:
            self.port_combobox.current(0)
    
    def toggle_connection(self):
        """Connect or disconnect from the ESP32"""
        if not self.connected:
            self.connect_to_esp()
        else:
            self.disconnect_from_esp()
    
    def connect_to_esp(self):
        """Establish serial connection to ESP32"""
        selected_port = self.port_combobox.get()
        if not selected_port:
            messagebox.showerror("Error", "No port selected")
            return
        
        with self.connect_lock:
            try:
                self.serial_port = serial.Serial(selected_port, 115200, timeout=1)
                time.sleep(2)  # Wait for ESP32 to reset
                self.connected = True
                self.status_label.config(text="Status: Connected", foreground="green")
                self.connect_button.config(text="Disconnect")
                
                # Request current settings from ESP32
                self.request_current_settings()
                # Read response and update GUI
                response = self.read_response()
                if response and response.get("status") == "ok":
                    self.update_gui_with_settings(response)
                else:
                    messagebox.showerror("Error", "Failed to retrieve settings from ESP32")
            except Exception as e:
                messagebox.showerror("Connection Error", f"Failed to connect: {str(e)}")
                self.serial_port = None
    
    def disconnect_from_esp(self):
        """Close the serial connection"""
        with self.connect_lock:
            if self.serial_port:
                self.serial_port.close()
                self.serial_port = None
            self.connected = False
            self.status_label.config(text="Status: Disconnected", foreground="red")
            self.connect_button.config(text="Connect")
    
    def request_current_settings(self):
        """Request the current signal generator settings from ESP32"""
        if not self.serial_port:
            return
        
        try:
            command = {"cmd": "get_settings"}
            self.serial_port.write((json.dumps(command) + "\n").encode())
        except Exception as e:
            messagebox.showerror("Communication Error", f"Failed to request settings: {str(e)}")
    
    def update_gui_with_settings(self, settings):
        """Update GUI elements with received settings"""
        # Update Channel 1
        ch1 = settings.get("channel1", {})
        self.channel_1_type.set(ch1.get("type", "Sine"))
        self.channel_1_freq.set(ch1.get("frequency", 1000.0))
        self.channel_1_phase.set(ch1.get("phase", 0.0))
        self.channel_1_enabled.set(ch1.get("enabled", True))
        
        # Update Channel 2
        ch2 = settings.get("channel2", {})
        self.channel_2_type.set(ch2.get("type", "Sine"))
        self.channel_2_freq.set(ch2.get("frequency", 1000.0))
        self.channel_2_phase.set(ch2.get("phase", 0.0))
        self.channel_2_enabled.set(ch2.get("enabled", True))
        
        # Update Modulation
        mod = settings.get("modulation", {})
        self.modulation_type.set(mod.get("type", "MFSK"))
        self.modulation_m.set(mod.get("m", 2))
        self.modulation_freq.set(mod.get("frequency", 100000.0))
        self.modulation_delta_freq.set(mod.get("delta_freq", 1000.0))  # Changed from min_max_freq
        self.modulation_baud_rate.set(mod.get("baud_rate", 1000.0))
        self.modulation_time.set(mod.get("mod_time", 10.0))
        data = mod.get("data", [])
        self.modulation_data.set(",".join(map(str, data)))
        self.modulation_enabled.set(mod.get("enabled", False))
        
        # Update channel checkbuttons based on modulation state
        self.toggle_modulation(self.modulation_enabled.get())
    
    def apply_channel_settings(self, channel, sig_type, freq, phase, enabled):
        """Send settings for a specific channel to ESP32"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to ESP32 first")
            return
        
        # Validate frequency
        if freq > 3000000:
            messagebox.showwarning("Invalid Frequency", "Maximum frequency is 3 MHz")
            return
            
        try:
            command = {
                "cmd": "set_channel",
                "channel": channel,
                "type": sig_type,
                "frequency": freq,
                "phase": phase,
                "enabled": enabled
            }
            
            self.serial_port.write((json.dumps(command) + "\n").encode())
            response = self.read_response()
            
            if response and response.get("status") == "ok":
                messagebox.showinfo("Success", f"Channel {channel} settings applied")
            else:
                error_msg = response.get("error", "Unknown error") if response else "No response"
                messagebox.showerror("Error", f"Failed to apply settings: {error_msg}")
        except Exception as e:
            messagebox.showerror("Communication Error", f"Failed to send settings: {str(e)}")
    
    def apply_modulation_settings(self, mod_type, m, freq, delta_freq, baud_rate, mod_time, data, enabled):
        """Send modulation settings to ESP32"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to ESP32 first")
            return
        
        # Parse data string if provided
        data_values = []
        if data:
            try:
                data_values = [int(x.strip()) for x in data.split(',')]
            except ValueError:
                messagebox.showwarning("Invalid Data", "Data must be comma-separated integers")
                return
        
        try:
            command = {
                "cmd": "set_modulation",
                "type": mod_type,
                "m": m,  # Add M parameter
                "frequency": freq,
                "delta_freq": delta_freq,
                "baud_rate": baud_rate,
                "mod_time": mod_time,
                "data": data_values,
                "enabled": enabled
            }
            
            self.serial_port.write((json.dumps(command) + "\n").encode())
            response = self.read_response()

            
            if response and response.get("status") == "ok":
                messagebox.showinfo("Success", "Modulation settings applied")
                
                # Update channel checkbuttons based on modulation state
                if enabled:
                    self.channel_1_enabled.set(False)
                    self.channel_2_enabled.set(False)
                    self.channel_1_enabled_check.state(['disabled'])
                    self.channel_2_enabled_check.state(['disabled'])
                else:
                    self.channel_1_enabled_check.state(['!disabled'])
                    self.channel_2_enabled_check.state(['!disabled'])
            else:
                error_msg = response.get("error", "Unknown error") if response else "No response"
                messagebox.showerror("Error", f"Failed to apply modulation settings: {error_msg}")
        except Exception as e:
            messagebox.showerror("Communication Error", f"Failed to send settings: {str(e)}")

    def apply_channel_settings_silent(self, channel, sig_type, freq, phase, enabled):
        """Send settings for a specific channel to ESP32 without showing messages"""
        if not self.connected:
            return False
        
        # Validate frequency
        if freq > 3000000:
            return False
            
        try:
            command = {
                "cmd": "set_channel",
                "channel": channel,
                "type": sig_type,
                "frequency": freq,
                "phase": phase,
                "enabled": enabled
            }
            
            self.serial_port.write((json.dumps(command) + "\n").encode())
            response = self.read_response()
            
            if response and response.get("status") == "ok":
                return True
            return False
        except Exception:
            return False

    def apply_modulation_settings_silent(self, mod_type, m, freq, delta_freq, baud_rate, mod_time, data, enabled):
        """Send modulation settings to ESP32 without showing messages"""
        if not self.connected:
            return False
        
        # Parse data string if provided
        data_values = []
        if data:
            try:
                data_values = [int(x.strip()) for x in data.split(',')]
            except ValueError:
                return False
        
        try:
            command = {
                "cmd": "set_modulation",
                "type": mod_type,
                "m": m,
                "frequency": freq,
                "delta_freq": delta_freq,
                "baud_rate": baud_rate,
                "mod_time": mod_time,
                "data": data_values,
                "enabled": enabled
            }
            
            self.serial_port.write((json.dumps(command) + "\n").encode())
            response = self.read_response()
            
            if response and response.get("status") == "ok":
                # Update channel checkbuttons based on modulation state
                if enabled:
                    self.channel_1_enabled.set(False)
                    self.channel_2_enabled.set(False)
                    self.channel_1_enabled_check.state(['disabled'])
                    self.channel_2_enabled_check.state(['disabled'])
                else:
                    self.channel_1_enabled_check.state(['!disabled'])
                    self.channel_2_enabled_check.state(['!disabled'])
                return True
            return False
        except Exception:
            return False
    
    def apply_all_settings(self):
        """Apply settings for all channels and modulation"""
        if not self.connected:
            messagebox.showwarning("Not Connected", "Please connect to ESP32 first")
            return
        
        # Track success status
        success = True
        error_message = ""
        
        # Check if modulation is enabled
        modulation_enabled = self.modulation_enabled.get()
        
        # Apply modulation settings first
        if not self.apply_modulation_settings_silent(
            self.modulation_type.get(),
            self.modulation_m.get(),
            self.modulation_freq.get(),
            self.modulation_delta_freq.get(),
            self.modulation_baud_rate.get(),
            self.modulation_time.get(),
            self.modulation_data.get(),
            modulation_enabled
        ):
            success = False
            error_message = "Failed to apply Modulation settings"
            
        # Only apply channel settings if modulation is disabled
        if success and not modulation_enabled:
            # Apply settings for channel 1
            if not self.apply_channel_settings_silent(
                1, 
                self.channel_1_type.get(),
                self.channel_1_freq.get(),
                self.channel_1_phase.get(),
                self.channel_1_enabled.get()
            ):
                success = False
                error_message = "Failed to apply Channel 1 settings"
            
            # Apply settings for channel 2
            if success and not self.apply_channel_settings_silent(
                2, 
                self.channel_2_type.get(),
                self.channel_2_freq.get(),
                self.channel_2_phase.get(),
                self.channel_2_enabled.get()
            ):
                success = False
                error_message = "Failed to apply Channel 2 settings"
        
        # Show single message based on result
        if success:
            messagebox.showinfo("Success", "Settings Applied!")
        else:
            messagebox.showerror("Error", error_message)
    
    def read_response(self):
        """Read response from ESP32"""
        if not self.serial_port:
            return None
        
        try:
            # Wait for response - increased timeout to 10 seconds
            start_time = time.time()
            while (time.time() - start_time) < 10:  # 10 second timeout (increased from 2)
                if self.serial_port.in_waiting:
                    response = self.serial_port.readline().decode().strip()
                    try:
                        return json.loads(response)
                    except json.JSONDecodeError:
                        return {"status": "error", "error": "Invalid response format"}
                # time.sleep(0.1)
            
            return {"status": "error", "error": "Timeout waiting for response"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    root = tk.Tk()
    app = SignalGeneratorGUI(root)
    root.mainloop()