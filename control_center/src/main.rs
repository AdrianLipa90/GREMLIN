#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use eframe::egui;
use serde_json::Value;
use std::io::Write;
use std::path::PathBuf;
use std::process::{Command, Stdio};

#[derive(Clone, Copy, PartialEq, Eq)]
enum Tab {
    Setup,
    Overview,
    License,
    Integrations,
    Settings,
    Diagnostics,
}

struct GremlinControlCenter {
    tab: Tab,
    doctor: Option<Value>,
    doctor_error: Option<String>,
    device: Option<Value>,
    device_error: Option<String>,
    license: Option<Value>,
    license_error: Option<String>,
    readiness: Option<Value>,
    readiness_error: Option<String>,
    providers: Option<Value>,
    provider_error: Option<String>,
    provider_result: Option<Value>,
    license_key_input: String,
    license_file_input: String,
    integration_path: String,
    integration_result: Option<Value>,
    integration_error: Option<String>,
}

impl Default for GremlinControlCenter {
    fn default() -> Self {
        let mut app = Self {
            tab: Tab::Setup,
            doctor: None,
            doctor_error: None,
            device: None,
            device_error: None,
            license: None,
            license_error: None,
            readiness: None,
            readiness_error: None,
            providers: None,
            provider_error: None,
            provider_result: None,
            license_key_input: String::new(),
            license_file_input: String::new(),
            integration_path: String::new(),
            integration_result: None,
            integration_error: None,
        };
        app.refresh_all();
        if app.ready_status() == "READY" {
            app.tab = Tab::Overview;
        }
        app
    }
}

fn ctl_program() -> PathBuf {
    if let Ok(current) = std::env::current_exe() {
        if let Some(parent) = current.parent() {
            let name = if cfg!(windows) { "gremlinctl.exe" } else { "gremlinctl" };
            let sibling = parent.join(name);
            if sibling.exists() {
                return sibling;
            }
        }
    }
    PathBuf::from(if cfg!(windows) { "gremlinctl.exe" } else { "gremlinctl" })
}

fn decode_ctl_output(output: std::process::Output) -> Result<Value, String> {
    if !output.status.success() && output.stdout.is_empty() {
        return Err(format!(
            "gremlinctl failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    serde_json::from_slice::<Value>(&output.stdout)
        .map_err(|err| format!("Could not decode gremlinctl JSON: {err}"))
}

fn run_ctl_json(args: &[String]) -> Result<Value, String> {
    let output = Command::new(ctl_program())
        .args(args)
        .output()
        .map_err(|err| format!("Could not launch gremlinctl: {err}"))?;
    decode_ctl_output(output)
}

fn run_ctl_json_input(args: &[String], input: &str) -> Result<Value, String> {
    let mut child = Command::new(ctl_program())
        .args(args)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|err| format!("Could not launch gremlinctl: {err}"))?;
    if let Some(mut stdin) = child.stdin.take() {
        stdin
            .write_all(input.as_bytes())
            .map_err(|err| format!("Could not pass license to gremlinctl: {err}"))?;
    }
    let output = child
        .wait_with_output()
        .map_err(|err| format!("Could not wait for gremlinctl: {err}"))?;
    decode_ctl_output(output)
}

impl GremlinControlCenter {
    fn refresh_all(&mut self) {
        self.refresh_license();
        self.refresh_doctor();
        self.refresh_device();
        self.refresh_providers();
        self.refresh_readiness();
    }

    fn refresh_doctor(&mut self) {
        self.doctor = None;
        self.doctor_error = None;
        match run_ctl_json(&["doctor".into(), "--json".into()]) {
            Ok(value) => self.doctor = Some(value),
            Err(err) => self.doctor_error = Some(err),
        }
    }

    fn refresh_device(&mut self) {
        self.device = None;
        self.device_error = None;
        match run_ctl_json(&["device".into(), "status".into(), "--json".into()]) {
            Ok(value) => self.device = Some(value),
            Err(err) => self.device_error = Some(err),
        }
    }

    fn refresh_license(&mut self) {
        self.license = None;
        self.license_error = None;
        match run_ctl_json(&["license".into(), "status".into(), "--json".into()]) {
            Ok(value) => self.license = Some(value),
            Err(err) => self.license_error = Some(err),
        }
    }

    fn refresh_readiness(&mut self) {
        self.readiness = None;
        self.readiness_error = None;
        match run_ctl_json(&["ready".into(), "--json".into()]) {
            Ok(value) => self.readiness = Some(value),
            Err(err) => self.readiness_error = Some(err),
        }
    }

    fn refresh_providers(&mut self) {
        self.providers = None;
        self.provider_error = None;
        match run_ctl_json(&["integrations".into(), "providers".into(), "--json".into()]) {
            Ok(value) => self.providers = Some(value),
            Err(err) => self.provider_error = Some(err),
        }
    }

    fn initialize_device(&mut self) {
        self.device_error = None;
        match run_ctl_json(&["device".into(), "init".into(), "--json".into()]) {
            Ok(_) => self.refresh_device(),
            Err(err) => self.device_error = Some(err),
        }
    }

    fn activate_license(&mut self) {
        self.license_error = None;
        let key = self.license_key_input.trim();
        if !key.starts_with("GRM1-") {
            self.license_error = Some("Paste the GREMLIN customer key beginning with GRM1-.".to_owned());
            return;
        }
        match run_ctl_json_input(
            &["license".into(), "activate".into(), "--stdin".into(), "--json".into()],
            key,
        ) {
            Ok(_) => {
                self.license_key_input.clear();
                self.initialize_device();
                self.refresh_all();
            }
            Err(err) => self.license_error = Some(err),
        }
    }

    fn import_license(&mut self) {
        self.license_error = None;
        let path = self.license_file_input.trim();
        if path.is_empty() {
            self.license_error = Some("Enter the path to the signed GREMLIN license.json file.".to_owned());
            return;
        }
        let args = vec![
            "license".to_owned(),
            "import".to_owned(),
            path.to_owned(),
            "--json".to_owned(),
        ];
        match run_ctl_json(&args) {
            Ok(_) => {
                self.initialize_device();
                self.refresh_all();
            }
            Err(err) => self.license_error = Some(err),
        }
    }

    fn provider_action(&mut self, action: &str, provider: &str) {
        self.provider_result = None;
        self.provider_error = None;
        let args = vec![
            "integrations".to_owned(),
            action.to_owned(),
            provider.to_owned(),
            "--json".to_owned(),
        ];
        match run_ctl_json(&args) {
            Ok(value) => {
                self.provider_result = Some(value);
                if action == "connect" {
                    let test_args = vec![
                        "integrations".to_owned(),
                        "test".to_owned(),
                        provider.to_owned(),
                        "--json".to_owned(),
                    ];
                    if let Ok(test_value) = run_ctl_json(&test_args) {
                        self.provider_result = Some(test_value);
                    }
                }
                self.refresh_providers();
                self.refresh_readiness();
            }
            Err(err) => self.provider_error = Some(err),
        }
    }

    fn integration_action(&mut self, action: &str) {
        self.integration_result = None;
        self.integration_error = None;
        let path = self.integration_path.trim();
        if path.is_empty() {
            self.integration_error = Some("Choose or enter an MCP client JSON config path.".to_owned());
            return;
        }
        let args = vec![
            "integrations".to_owned(), action.to_owned(), "--config".to_owned(),
            path.to_owned(), "--json".to_owned(),
        ];
        match run_ctl_json(&args) {
            Ok(value) => {
                self.integration_result = Some(value);
                self.refresh_readiness();
            }
            Err(err) => self.integration_error = Some(err),
        }
    }

    fn overall_status(&self) -> &str {
        self.doctor.as_ref().and_then(|v| v.get("status")).and_then(Value::as_str).unwrap_or("UNAVAILABLE")
    }

    fn license_status(&self) -> &str {
        self.license.as_ref().and_then(|v| v.get("status")).and_then(Value::as_str).unwrap_or("NOT_ACTIVATED")
    }

    fn license_active(&self) -> bool {
        self.license_status() == "ACTIVE"
    }

    fn product_status(&self) -> &str {
        self.readiness.as_ref().and_then(|v| v.get("product")).and_then(|v| v.get("status")).and_then(Value::as_str)
            .or_else(|| self.doctor.as_ref().and_then(|v| v.get("product")).and_then(|v| v.get("status")).and_then(Value::as_str))
            .unwrap_or("NOT ACTIVATED")
    }

    fn ready_status(&self) -> &str {
        self.readiness.as_ref().and_then(|v| v.get("status")).and_then(Value::as_str).unwrap_or("ACTION_REQUIRED")
    }

    fn device_status(&self) -> &str {
        self.device.as_ref().and_then(|v| v.get("identity")).and_then(|v| v.get("status")).and_then(Value::as_str)
            .unwrap_or_else(|| self.device.as_ref().and_then(|v| v.get("status")).and_then(Value::as_str).unwrap_or("UNAVAILABLE"))
    }

    fn runtime_transport(&self) -> &str {
        self.doctor.as_ref().and_then(|v| v.get("config")).and_then(|v| v.get("runtime")).and_then(|v| v.get("transport")).and_then(Value::as_str).unwrap_or("stdio")
    }

    fn platform_name(&self) -> &str {
        self.providers.as_ref().and_then(|v| v.get("platform")).and_then(Value::as_str)
            .map(|v| if v == "windows" { "Windows x64" } else { "Linux amd64" })
            .unwrap_or(if cfg!(windows) { "Windows x64" } else { "Linux amd64" })
    }

    fn nav(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.selectable_value(&mut self.tab, Tab::Setup, "Setup");
            ui.selectable_value(&mut self.tab, Tab::Overview, "Overview");
            ui.selectable_value(&mut self.tab, Tab::License, "License");
            ui.selectable_value(&mut self.tab, Tab::Integrations, "AI Providers");
            ui.selectable_value(&mut self.tab, Tab::Settings, "Settings");
            ui.selectable_value(&mut self.tab, Tab::Diagnostics, "Diagnostics");
        });
    }

    fn license_activation_panel(&mut self, ui: &mut egui::Ui) {
        if self.license_active() {
            ui.strong("✓ License active");
            if let Some(info) = self.license.as_ref().and_then(|v| v.get("license")) {
                if let Some(edition) = info.get("edition").and_then(Value::as_str) {
                    ui.label(format!("Edition: {edition}"));
                }
                if let Some(id) = info.get("license_id").and_then(Value::as_str) {
                    ui.label(format!("License ID: {id}"));
                }
            }
            return;
        }

        ui.label("Paste the customer license key you received after purchase.");
        ui.add(
            egui::TextEdit::singleline(&mut self.license_key_input)
                .password(true)
                .hint_text("GRM1-...")
                .desired_width(f32::INFINITY),
        );
        ui.horizontal(|ui| {
            if ui.button("Activate GREMLIN").clicked() {
                self.activate_license();
            }
            if ui.button("Refresh license").clicked() {
                self.refresh_license();
                self.refresh_readiness();
            }
        });
        ui.small("Activation is verified locally against the issuer signature. The key is passed to the local GREMLIN process through stdin, not as a command-line argument.");
        ui.add_space(8.0);
        egui::CollapsingHeader::new("I received a signed license.json instead")
            .default_open(false)
            .show(ui, |ui| {
                ui.text_edit_singleline(&mut self.license_file_input);
                if ui.button("Import signed license file").clicked() {
                    self.import_license();
                }
            });
        if let Some(err) = &self.license_error {
            ui.add_space(8.0);
            ui.label(err);
        }
    }

    fn setup(&mut self, ui: &mut egui::Ui) {
        ui.heading("Get GREMLIN ready");
        ui.label("Three steps. No terminal and no manual MCP configuration required for supported clients.");
        ui.add_space(14.0);

        egui::Frame::group(ui.style()).show(ui, |ui| {
            ui.heading("1. Activate");
            self.license_activation_panel(ui);
        });

        ui.add_space(12.0);
        egui::Frame::group(ui.style()).show(ui, |ui| {
            ui.heading("2. Connect your AI client");
            if !self.license_active() {
                ui.label("Activate GREMLIN first. Provider controls will unlock automatically.");
                return;
            }
            let providers_owned: Vec<Value> = self.providers.as_ref()
                .and_then(|v| v.get("providers"))
                .and_then(Value::as_array)
                .cloned()
                .unwrap_or_default();
            let detected: Vec<Value> = providers_owned.into_iter()
                .filter(|p| p.get("detected").and_then(Value::as_bool).unwrap_or(false))
                .collect();
            if detected.is_empty() {
                ui.label("No supported AI client detected yet. Install or open Codex, OpenCode, Claude Code, Gemini CLI, Cursor, VS Code/Copilot or Windsurf, then click Refresh.");
                if cfg!(windows) {
                    ui.label("Claude Desktop is also supported in the Windows build.");
                }
                if ui.button("Refresh detection").clicked() {
                    self.refresh_providers();
                    self.refresh_readiness();
                }
            } else {
                for provider in &detected {
                    self.provider_card(ui, provider);
                    ui.add_space(8.0);
                }
            }
        });

        ui.add_space(12.0);
        egui::Frame::group(ui.style()).show(ui, |ui| {
            ui.heading("3. Ready");
            ui.strong(self.ready_status());
            if self.ready_status() == "READY" {
                ui.label("GREMLIN is licensed, the local MCP runtime is available and at least one AI client is connected.");
                if ui.button("Open GREMLIN").clicked() {
                    self.tab = Tab::Overview;
                }
            } else if let Some(actions) = self.readiness.as_ref().and_then(|v| v.get("actions")).and_then(Value::as_array) {
                for action in actions {
                    if let Some(text) = action.as_str() {
                        ui.label(format!("• {text}"));
                    }
                }
            }
            if ui.button("Check again").clicked() {
                self.refresh_all();
            }
            if let Some(err) = &self.readiness_error {
                ui.label(err);
            }
        });
    }

    fn overview(&mut self, ui: &mut egui::Ui) {
        ui.heading("GREMLIN AI Research Orchestrator");
        ui.label(format!("{} edition", self.platform_name()));
        ui.add_space(8.0);
        egui::Grid::new("overview_status").num_columns(2).spacing([24.0, 12.0]).show(ui, |ui| {
            ui.label("Ready"); ui.strong(self.ready_status()); ui.end_row();
            ui.label("System"); ui.strong(self.overall_status()); ui.end_row();
            ui.label("Platform"); ui.strong(self.platform_name()); ui.end_row();
            ui.label("License"); ui.strong(self.license_status()); ui.end_row();
            ui.label("Product"); ui.strong(self.product_status()); ui.end_row();
            ui.label("MCP transport"); ui.strong(self.runtime_transport()); ui.end_row();
        });
        ui.add_space(16.0);
        ui.horizontal(|ui| {
            if ui.button("AI Providers").clicked() {
                self.tab = Tab::Integrations;
            }
            if ui.button("Run readiness check").clicked() {
                self.refresh_all();
            }
            if self.ready_status() != "READY" && ui.button("Resume setup").clicked() {
                self.tab = Tab::Setup;
            }
        });
    }

    fn license(&mut self, ui: &mut egui::Ui) {
        ui.heading("License");
        self.license_activation_panel(ui);
        ui.add_space(16.0);
        egui::CollapsingHeader::new("Device identity")
            .default_open(false)
            .show(ui, |ui| {
                ui.label(format!("Device identity: {}", self.device_status()));
                if let Some(device_id) = self.device.as_ref().and_then(|v| v.get("identity")).and_then(|v| v.get("device_id")).and_then(Value::as_str) {
                    ui.label(format!("Device ID: {device_id}"));
                }
                if ui.button("Repair / initialize device identity").clicked() {
                    self.initialize_device();
                }
                if let Some(err) = &self.device_error {
                    ui.label(err);
                }
            });
    }

    fn provider_card(&mut self, ui: &mut egui::Ui, provider: &Value) {
        let id = provider.get("provider_id").and_then(Value::as_str).unwrap_or("unknown");
        let name = provider.get("display_name").and_then(Value::as_str).unwrap_or(id);
        let detected = provider.get("detected").and_then(Value::as_bool).unwrap_or(false);
        let connected = provider.get("connected").and_then(Value::as_bool).unwrap_or(false);
        let status = provider.get("connection_status").and_then(Value::as_str).unwrap_or("UNKNOWN");
        let executable = provider.get("executable").and_then(Value::as_str).unwrap_or("Not found");
        let config = provider.get("config_path").and_then(Value::as_str).unwrap_or("Managed by client");
        let mode = provider.get("integration_mode").and_then(Value::as_str).unwrap_or("MCP");

        egui::Frame::group(ui.style()).show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.heading(name);
                ui.separator();
                ui.strong(status);
            });
            ui.label(format!("Integration: {}", if mode == "NATIVE_CLI" { "Native client MCP interface" } else { "Safe config merge" }));
            ui.label(format!("Client detected: {}", if detected { "yes" } else { "no" }));
            if detected { ui.label(format!("Executable: {executable}")); }
            ui.label(format!("Config: {config}"));
            ui.add_space(8.0);
            ui.horizontal(|ui| {
                if ui.add_enabled(self.license_active() && detected && !connected, egui::Button::new("Connect & Test")).clicked() {
                    self.provider_action("connect", id);
                }
                if ui.add_enabled(self.license_active() && detected, egui::Button::new("Test MCP")).clicked() {
                    self.provider_action("test", id);
                }
                if ui.add_enabled(detected && connected, egui::Button::new("Disconnect")).clicked() {
                    self.provider_action("disconnect", id);
                }
            });
            if let Some(detail) = provider.get("detail").and_then(Value::as_str) {
                if !detail.is_empty() { ui.add_space(6.0); ui.small(detail); }
            }
        });
    }

    fn integrations(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.heading(format!("AI Providers — {}", self.platform_name()));
            if ui.button("Refresh detection").clicked() {
                self.refresh_providers();
                self.refresh_readiness();
            }
        });
        ui.label("Select your client and press Connect & Test. GREMLIN uses the client's native MCP interface where available and an atomic backed-up config merge otherwise.");
        ui.add_space(12.0);

        let providers_owned: Vec<Value> = self.providers.as_ref()
            .and_then(|v| v.get("providers"))
            .and_then(Value::as_array)
            .cloned()
            .unwrap_or_default();
        if providers_owned.is_empty() {
            ui.label("No supported AI clients are available for this platform.");
        } else {
            for provider in &providers_owned {
                self.provider_card(ui, provider);
                ui.add_space(10.0);
            }
        }
        if let Some(err) = &self.provider_error { ui.label(err); }
        if let Some(result) = &self.provider_result {
            ui.add_space(6.0);
            let status = result.get("status").and_then(Value::as_str).unwrap_or("DONE");
            ui.strong(format!("Last connection check: {status}"));
            if let Some(detail) = result.get("detail").and_then(Value::as_str) { if !detail.is_empty() { ui.label(detail); } }
        }

        ui.add_space(12.0);
        egui::CollapsingHeader::new("Advanced: Custom MCP client")
            .default_open(false)
            .show(ui, |ui| {
                ui.label("Use this only for clients that expose a standard JSON mcpServers configuration.");
                ui.horizontal(|ui| { ui.label("Config file"); ui.text_edit_singleline(&mut self.integration_path); });
                ui.horizontal(|ui| {
                    if ui.button("Inspect").clicked() { self.integration_action("inspect"); }
                    if ui.add_enabled(self.license_active(), egui::Button::new("Connect")).clicked() { self.integration_action("install"); }
                    if ui.button("Remove").clicked() { self.integration_action("remove"); }
                });
                if let Some(err) = &self.integration_error { ui.label(err); }
                if let Some(result) = &self.integration_result {
                    let mut text = serde_json::to_string_pretty(result).unwrap_or_else(|_| "{}".to_owned());
                    ui.add(egui::TextEdit::multiline(&mut text).font(egui::TextStyle::Monospace).desired_rows(10).interactive(false));
                }
            });
    }

    fn settings(&mut self, ui: &mut egui::Ui) {
        ui.heading("Settings");
        ui.label(format!("Platform package: {}", self.platform_name()));
        ui.label(format!("Effective transport: {}", self.runtime_transport()));
        ui.label("Default local integration uses stdio. Provider connections, licensing and optional device binding remain separate security layers.");
    }

    fn diagnostics(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.heading("Diagnostics");
            if ui.button("Refresh").clicked() { self.refresh_all(); }
        });
        ui.separator();
        if let Some(value) = &self.readiness {
            ui.heading("Customer readiness");
            let mut text = serde_json::to_string_pretty(value).unwrap_or_else(|_| "{}".to_owned());
            ui.add(egui::TextEdit::multiline(&mut text).font(egui::TextStyle::Monospace).desired_rows(12).interactive(false));
        }
        ui.add_space(10.0);
        if let Some(value) = &self.doctor {
            ui.heading("Doctor");
            let mut text = serde_json::to_string_pretty(value).unwrap_or_else(|_| "{}".to_owned());
            ui.add(egui::TextEdit::multiline(&mut text).font(egui::TextStyle::Monospace).desired_rows(18).interactive(false));
        } else if let Some(err) = &self.doctor_error { ui.label(err); } else { ui.label("Diagnostics unavailable."); }
    }
}

impl eframe::App for GremlinControlCenter {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::TopBottomPanel::top("top_bar").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.strong("GREMLIN Control Center");
                ui.separator();
                ui.label(self.platform_name());
                ui.separator();
                ui.strong(self.ready_status());
            });
            self.nav(ui);
        });
        egui::CentralPanel::default().show(ctx, |ui| match self.tab {
            Tab::Setup => self.setup(ui),
            Tab::Overview => self.overview(ui),
            Tab::License => self.license(ui),
            Tab::Integrations => self.integrations(ui),
            Tab::Settings => self.settings(ui),
            Tab::Diagnostics => self.diagnostics(ui),
        });
    }
}

fn main() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1000.0, 760.0])
            .with_min_inner_size([780.0, 560.0]),
        ..Default::default()
    };
    eframe::run_native(
        "GREMLIN Control Center",
        options,
        Box::new(|_cc| Ok(Box::<GremlinControlCenter>::default())),
    )
}
