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
    profile: Option<Value>,
    profile_error: Option<String>,
    readiness: Option<Value>,
    readiness_error: Option<String>,
    providers: Option<Value>,
    provider_error: Option<String>,
    provider_result: Option<Value>,
    license_key_input: String,
    license_file_input: String,
    profile_file_input: String,
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
            profile: None,
            profile_error: None,
            readiness: None,
            readiness_error: None,
            providers: None,
            provider_error: None,
            provider_result: None,
            license_key_input: String::new(),
            license_file_input: String::new(),
            profile_file_input: String::new(),
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
    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr).trim().to_owned();
        let stdout = String::from_utf8_lossy(&output.stdout).trim().to_owned();
        let detail = if !stderr.is_empty() {
            stderr
        } else if !stdout.is_empty() {
            stdout
        } else {
            "no diagnostic output".to_owned()
        };
        return Err(format!("gremlinctl failed ({}): {detail}", output.status));
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
    fn configure_style(ctx: &egui::Context) {
        let mut visuals = egui::Visuals::dark();
        visuals.panel_fill = egui::Color32::from_rgb(8, 10, 20);
        visuals.window_fill = egui::Color32::from_rgb(10, 12, 24);
        visuals.extreme_bg_color = egui::Color32::from_rgb(5, 7, 15);
        visuals.faint_bg_color = egui::Color32::from_rgb(18, 20, 36);
        visuals.selection.bg_fill = egui::Color32::from_rgb(85, 50, 190);
        visuals.selection.stroke.color = egui::Color32::from_rgb(208, 190, 255);
        visuals.hyperlink_color = egui::Color32::from_rgb(111, 216, 255);
        visuals.warn_fg_color = egui::Color32::from_rgb(255, 198, 92);
        visuals.error_fg_color = egui::Color32::from_rgb(255, 110, 135);
        visuals.widgets.inactive.bg_fill = egui::Color32::from_rgb(20, 23, 42);
        visuals.widgets.hovered.bg_fill = egui::Color32::from_rgb(39, 30, 75);
        visuals.widgets.active.bg_fill = egui::Color32::from_rgb(70, 43, 140);
        ctx.set_visuals(visuals);
        ctx.style_mut(|style| {
            style.spacing.item_spacing = egui::vec2(10.0, 8.0);
            style.spacing.button_padding = egui::vec2(12.0, 7.0);
        });
    }

    fn status_color(status: &str) -> egui::Color32 {
        match status {
            "READY" | "ACTIVE" | "LICENSED" | "CONNECTED" | "PASS" | "OK" => egui::Color32::from_rgb(104, 224, 169),
            "ACTION_REQUIRED" | "CONFIGURED_UNVERIFIED" | "REGISTERED_UNVERIFIED" | "NOT_CONFIGURED" | "DETECTED" => egui::Color32::from_rgb(255, 196, 92),
            "ERROR" | "FAILED" | "FAIL" | "BLOCKED" | "INVALID" | "UNAVAILABLE" => egui::Color32::from_rgb(255, 110, 135),
            _ => egui::Color32::from_rgb(119, 190, 255),
        }
    }

    fn status_label(ui: &mut egui::Ui, status: &str) {
        ui.colored_label(
            Self::status_color(status),
            egui::RichText::new(status.replace('_', " ")).strong(),
        );
    }

    fn provider_counts(&self) -> (usize, usize) {
        let providers = self.providers.as_ref()
            .and_then(|v| v.get("providers"))
            .and_then(Value::as_array);
        let detected = providers.map(|items| items.iter().filter(|p| p.get("detected").and_then(Value::as_bool).unwrap_or(false)).count()).unwrap_or(0);
        let connected = providers.map(|items| items.iter().filter(|p| p.get("connected").and_then(Value::as_bool).unwrap_or(false)).count()).unwrap_or(0);
        (detected, connected)
    }

    fn next_action(&self) -> String {
        if self.ready_status() == "READY" {
            return "GREMLIN is ready. Open a connected AI client and use GREMLIN through MCP.".to_owned();
        }
        if !self.license_active() {
            return "Activate your GREMLIN license to unlock provider connection controls.".to_owned();
        }
        if self.product_status() != "LICENSED" {
            return if self.profile_required() {
                "Import and verify the customer profile required by this license.".to_owned()
            } else {
                "Complete the remaining product entitlement step.".to_owned()
            };
        }
        if !self.runtime_available() {
            return "GREMLIN runtime is unavailable. Open Diagnostics and repair or reinstall the local runtime before connecting an AI client.".to_owned();
        }
        let (detected, connected) = self.provider_counts();
        if connected == 0 {
            return if detected > 0 {
                "Choose a detected AI client and press Connect & Test.".to_owned()
            } else {
                "Open or install a supported AI client, then refresh detection.".to_owned()
            };
        }
        if let Some(action) = self.readiness.as_ref()
            .and_then(|v| v.get("actions"))
            .and_then(Value::as_array)
            .and_then(|items| items.iter().find_map(Value::as_str))
        {
            return action.to_owned();
        }
        "Run the readiness check to identify the remaining action.".to_owned()
    }

    fn readiness_strip(&self, ui: &mut egui::Ui) {
        let (detected, connected) = self.provider_counts();
        ui.horizontal_wrapped(|ui| {
            ui.strong("License");
            Self::status_label(ui, if self.license_active() { "ACTIVE" } else { "ACTION_REQUIRED" });
            ui.separator();
            ui.strong("Product");
            Self::status_label(ui, self.product_status());
            ui.separator();
            ui.strong("Runtime");
            Self::status_label(ui, if self.runtime_available() { "ACTIVE" } else { "UNAVAILABLE" });
            ui.separator();
            ui.strong("AI client");
            Self::status_label(ui, if connected > 0 { "CONNECTED" } else if detected > 0 { "DETECTED" } else { "ACTION_REQUIRED" });
            ui.separator();
            ui.strong("Readiness");
            Self::status_label(ui, self.ready_status());
        });
    }

    fn refresh_all(&mut self) {
        self.refresh_license();
        self.refresh_profile();
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

    fn refresh_profile(&mut self) {
        self.profile = None;
        self.profile_error = None;
        match run_ctl_json(&["profile".into(), "status".into(), "--json".into()]) {
            Ok(value) => self.profile = Some(value),
            Err(err) => self.profile_error = Some(err),
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
            self.license_error = Some("Drop or enter the signed GREMLIN license.json file.".to_owned());
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

    fn import_profile(&mut self) {
        self.profile_error = None;
        let path = self.profile_file_input.trim();
        if path.is_empty() {
            self.profile_error = Some("Drop or enter the customer profile JSON file.".to_owned());
            return;
        }
        let args = vec![
            "profile".to_owned(),
            "import".to_owned(),
            path.to_owned(),
            "--json".to_owned(),
        ];
        match run_ctl_json(&args) {
            Ok(_) => self.refresh_all(),
            Err(err) => self.profile_error = Some(err),
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
                let test_error = if action == "connect" {
                    let test_args = vec![
                        "integrations".to_owned(),
                        "test".to_owned(),
                        provider.to_owned(),
                        "--json".to_owned(),
                    ];
                    match run_ctl_json(&test_args) {
                        Ok(test_value) => {
                            self.provider_result = Some(test_value);
                            None
                        }
                        Err(err) => Some(err),
                    }
                } else {
                    None
                };
                self.refresh_providers();
                self.refresh_readiness();
                if let Some(err) = test_error {
                    let test_message = format!("Provider connected, but MCP test failed: {err}");
                    self.provider_error = Some(match self.provider_error.take() {
                        Some(existing) => format!("{existing}; {test_message}"),
                        None => test_message,
                    });
                }
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

    fn handle_dropped_files(&mut self, ctx: &egui::Context) {
        let paths: Vec<PathBuf> = ctx.input(|input| {
            input.raw.dropped_files.iter().filter_map(|file| file.path.clone()).collect()
        });
        if let Some(path) = paths.last() {
            let text = path.to_string_lossy().to_string();
            if path.extension().and_then(|v| v.to_str()).map(|v| v.eq_ignore_ascii_case("json")).unwrap_or(false) {
                self.license_file_input = text.clone();
                self.profile_file_input = text;
            }
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

    fn profile_status(&self) -> &str {
        self.profile.as_ref().and_then(|v| v.get("status")).and_then(Value::as_str).unwrap_or("NOT_CONFIGURED")
    }

    fn profile_required(&self) -> bool {
        self.readiness.as_ref()
            .and_then(|v| v.get("product"))
            .and_then(|v| v.get("reason"))
            .and_then(Value::as_str)
            == Some("required client profile is missing")
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
    fn runtime_available(&self) -> bool {
        self.readiness.as_ref()
            .and_then(|v| v.get("runtime"))
            .and_then(|v| v.get("available"))
            .and_then(Value::as_bool)
            .unwrap_or(false)
    }

    fn runtime_transport(&self) -> &str {
        self.readiness.as_ref()
            .and_then(|v| v.get("runtime"))
            .and_then(|v| v.get("transport"))
            .and_then(Value::as_str)
            .or_else(|| self.doctor.as_ref().and_then(|v| v.get("config")).and_then(|v| v.get("runtime")).and_then(|v| v.get("transport")).and_then(Value::as_str))
            .unwrap_or("stdio")
    }

    fn platform_name(&self) -> &str {
        self.providers.as_ref().and_then(|v| v.get("platform")).and_then(Value::as_str)
            .map(|v| if v == "windows" { "Windows x64" } else { "Linux amd64" })
            .unwrap_or(if cfg!(windows) { "Windows x64" } else { "Linux amd64" })
    }

    fn nav(&mut self, ui: &mut egui::Ui) {
        ui.vertical(|ui| {
            ui.selectable_value(&mut self.tab, Tab::Overview, "Overview");
            ui.selectable_value(&mut self.tab, Tab::Setup, "Setup");
            ui.selectable_value(&mut self.tab, Tab::Integrations, "AI Providers");
            ui.selectable_value(&mut self.tab, Tab::License, "License");
            ui.selectable_value(&mut self.tab, Tab::Diagnostics, "Diagnostics");
            ui.selectable_value(&mut self.tab, Tab::Settings, "Settings");
        });
        ui.add_space(12.0);
        ui.separator();
        ui.add_space(8.0);
        ui.small("18-role Bestiary");
        ui.small("PhaseNav 36D");
        ui.small("fail-closed receipts");
        ui.small("local MCP control plane");
    }

    fn profile_import_controls(&mut self, ui: &mut egui::Ui) {
        ui.label("Drop the customer profile JSON onto this window, or enter its file path:");
        ui.text_edit_singleline(&mut self.profile_file_input);
        if ui.button("Import & verify customer profile").clicked() {
            self.import_profile();
        }
        if let Some(err) = &self.profile_error {
            ui.label(err);
        }
    }

    fn customer_profile_panel(&mut self, ui: &mut egui::Ui) {
        ui.add_space(10.0);
        ui.separator();
        ui.strong("Customer profile");
        match self.profile_status() {
            "ACTIVE" => {
                ui.label("✓ Customer profile active");
                if let Some(profile) = &self.profile {
                    if let Some(label) = profile.get("label").and_then(Value::as_str) {
                        if !label.is_empty() { ui.label(format!("Profile: {label}")); }
                    }
                    if let Some(commitment) = profile.get("profile_commitment").and_then(Value::as_str) {
                        ui.small(format!("Commitment: {commitment}"));
                    }
                }
            }
            _ if self.profile_required() => {
                ui.strong("Required by this signed license");
                self.profile_import_controls(ui);
            }
            _ => {
                egui::CollapsingHeader::new("Customer-specific profile (optional for this license)")
                    .default_open(false)
                    .show(ui, |ui| self.profile_import_controls(ui));
            }
        }
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
            self.customer_profile_panel(ui);
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
                ui.label("Drop the file onto this window or enter the path:");
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
        ui.heading("Set up GREMLIN");
        ui.label("Three guided steps. No terminal and no manual MCP editing for supported clients.");
        ui.add_space(8.0);
        self.readiness_strip(ui);
        ui.add_space(8.0);
        ui.colored_label(
            Self::status_color(self.ready_status()),
            egui::RichText::new(self.next_action()).strong(),
        );
        ui.add_space(16.0);

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
            if self.product_status() != "LICENSED" {
                ui.label("Complete the required entitlement/profile step above first.");
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
                if ui.button("Go to Overview").clicked() {
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
        ui.horizontal_wrapped(|ui| {
            ui.heading("GREMLIN");
            ui.separator();
            Self::status_label(ui, self.ready_status());
        });
        ui.label("Local AI orchestration control plane — connect your existing AI client, keep lineage visible, and fail closed when evidence is incomplete.");
        ui.add_space(12.0);

        egui::Frame::group(ui.style()).show(ui, |ui| {
            ui.strong("Next action");
            ui.add_space(4.0);
            ui.label(self.next_action());
            if self.ready_status() != "READY" {
                ui.add_space(6.0);
                if ui.button("Resume setup").clicked() {
                    self.tab = Tab::Setup;
                }
            }
        });

        ui.add_space(12.0);
        self.readiness_strip(ui);
        ui.add_space(16.0);

        let (detected, connected) = self.provider_counts();
        egui::Grid::new("overview_status_v2")
            .num_columns(3)
            .spacing([20.0, 12.0])
            .striped(true)
            .show(ui, |ui| {
                ui.strong("System");
                Self::status_label(ui, self.overall_status());
                ui.label(self.platform_name());
                ui.end_row();

                ui.strong("License");
                Self::status_label(ui, self.license_status());
                ui.label(self.product_status());
                ui.end_row();

                ui.strong("AI providers");
                Self::status_label(ui, if connected > 0 { "CONNECTED" } else if detected > 0 { "DETECTED" } else { "ACTION_REQUIRED" });
                ui.label(format!("{connected} connected / {detected} detected"));
                ui.end_row();

                ui.strong("MCP runtime");
                Self::status_label(ui, if self.runtime_available() { "ACTIVE" } else { "UNAVAILABLE" });
                ui.label(self.runtime_transport());
                ui.end_row();

                ui.strong("Customer profile");
                Self::status_label(ui, self.profile_status());
                ui.label(if self.profile_required() { "required by entitlement" } else { "optional unless licensed profile requires it" });
                ui.end_row();

                ui.strong("Device identity");
                Self::status_label(ui, self.device_status());
                ui.label("local identity / license binding");
                ui.end_row();
            });

        ui.add_space(18.0);
        ui.horizontal_wrapped(|ui| {
            if ui.button("AI Providers").clicked() {
                self.tab = Tab::Integrations;
            }
            if ui.button("Run readiness check").clicked() {
                self.refresh_all();
            }
            if ui.button("Diagnostics").clicked() {
                self.tab = Tab::Diagnostics;
            }
        });

        ui.add_space(18.0);
        egui::Frame::group(ui.style()).show(ui, |ui| {
            ui.strong("What GREMLIN adds");
            ui.label("18-role Bestiary • geometry/phase/state scheduling • durable worker state • fail-closed lineage • local-first MCP integration");
        });
    }

    fn license(&mut self, ui: &mut egui::Ui) {
        ui.heading("License & customer profile");
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
        let raw_status = provider.get("connection_status").and_then(Value::as_str).unwrap_or("UNKNOWN");
        let status = if connected { "CONNECTED" } else if detected && raw_status == "UNKNOWN" { "DETECTED" } else { raw_status };
        let executable = provider.get("executable").and_then(Value::as_str).unwrap_or("Not found");
        let config = provider.get("config_path").and_then(Value::as_str).unwrap_or("Managed by client");
        let mode = provider.get("integration_mode").and_then(Value::as_str).unwrap_or("MCP");

        egui::Frame::group(ui.style()).show(ui, |ui| {
            ui.horizontal_wrapped(|ui| {
                ui.heading(name);
                ui.separator();
                Self::status_label(ui, status);
                if detected {
                    ui.small("detected locally");
                }
            });

            ui.label(if connected {
                "GREMLIN is configured for this client. Test MCP to verify the live client/runtime path."
            } else if detected {
                "Client detected. GREMLIN can connect it without manual MCP editing."
            } else {
                "Client not detected on this machine."
            });

            ui.add_space(8.0);
            let product_ready = self.product_status() == "LICENSED";
            ui.horizontal_wrapped(|ui| {
                if ui.add_enabled(product_ready && detected && !connected, egui::Button::new("Connect & Test")).clicked() {
                    self.provider_action("connect", id);
                }
                if ui.add_enabled(product_ready && detected, egui::Button::new("Test MCP")).clicked() {
                    self.provider_action("test", id);
                }
                if ui.add_enabled(detected && connected, egui::Button::new("Disconnect")).clicked() {
                    self.provider_action("disconnect", id);
                }
            });

            egui::CollapsingHeader::new("Technical details")
                .default_open(false)
                .show(ui, |ui| {
                    ui.label(format!("Integration mode: {}", if mode == "NATIVE_CLI" { "Native client MCP interface" } else { "Safe config merge" }));
                    if detected { ui.label(format!("Executable: {executable}")); }
                    ui.label(format!("Config: {config}"));
                    if let Some(detail) = provider.get("detail").and_then(Value::as_str) {
                        if !detail.is_empty() { ui.small(detail); }
                    }
                });
        });
    }

    fn integrations(&mut self, ui: &mut egui::Ui) {
        let (detected_count, connected_count) = self.provider_counts();
        ui.horizontal_wrapped(|ui| {
            ui.heading("AI Providers");
            ui.separator();
            ui.label(format!("{connected_count} connected • {detected_count} detected • {}", self.platform_name()));
            if ui.button("Refresh").clicked() {
                self.refresh_providers();
                self.refresh_readiness();
            }
        });
        ui.label("Connect the AI tools you already use. GREMLIN prefers each client's native MCP interface and uses an atomic backed-up config merge only where necessary.");
        ui.add_space(12.0);

        let mut providers_owned: Vec<Value> = self.providers.as_ref()
            .and_then(|v| v.get("providers"))
            .and_then(Value::as_array)
            .cloned()
            .unwrap_or_default();
        providers_owned.sort_by_key(|p| {
            let connected = p.get("connected").and_then(Value::as_bool).unwrap_or(false);
            let detected = p.get("detected").and_then(Value::as_bool).unwrap_or(false);
            if connected { 0 } else if detected { 1 } else { 2 }
        });

        if providers_owned.is_empty() {
            ui.label("No supported AI clients are available for this platform.");
        } else {
            for provider in &providers_owned {
                self.provider_card(ui, provider);
                ui.add_space(10.0);
            }
        }

        if let Some(err) = &self.provider_error {
            ui.colored_label(egui::Color32::from_rgb(255, 110, 135), err);
        }
        if let Some(result) = &self.provider_result {
            ui.add_space(6.0);
            let status = result.get("status").and_then(Value::as_str).unwrap_or("DONE");
            ui.horizontal_wrapped(|ui| {
                ui.strong("Last connection check");
                Self::status_label(ui, status);
            });
            if let Some(detail) = result.get("detail").and_then(Value::as_str) {
                if !detail.is_empty() { ui.label(detail); }
            }
        }

        ui.add_space(12.0);
        egui::CollapsingHeader::new("Advanced: Custom MCP client")
            .default_open(false)
            .show(ui, |ui| {
                ui.label("For unsupported clients that expose a standard JSON mcpServers configuration.");
                ui.horizontal(|ui| { ui.label("Config file"); ui.text_edit_singleline(&mut self.integration_path); });
                ui.horizontal_wrapped(|ui| {
                    if ui.button("Inspect").clicked() { self.integration_action("inspect"); }
                    if ui.add_enabled(self.product_status() == "LICENSED", egui::Button::new("Connect")).clicked() { self.integration_action("install"); }
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
        ui.label("GREMLIN is local-first by default. Normal desktop integrations use stdio and do not require a listening network port.");
        ui.add_space(12.0);
        egui::Grid::new("settings_summary").num_columns(2).spacing([24.0, 12.0]).show(ui, |ui| {
            ui.label("Platform package"); ui.strong(self.platform_name()); ui.end_row();
            ui.label("Effective MCP transport"); ui.strong(self.runtime_transport()); ui.end_row();
            ui.label("Product status"); Self::status_label(ui, self.product_status()); ui.end_row();
            ui.label("Device identity"); Self::status_label(ui, self.device_status()); ui.end_row();
        });
        ui.add_space(14.0);
        ui.label("Provider connections, licensing, customer-profile policy and device binding remain separate security layers. A configured provider is not presented as a verified live MCP connection until the test succeeds.");
    }

    fn diagnostics(&mut self, ui: &mut egui::Ui) {
        ui.horizontal_wrapped(|ui| {
            ui.heading("Diagnostics");
            if ui.button("Refresh").clicked() { self.refresh_all(); }
        });
        ui.label("Start with the human-readable action below. Raw receipts are available only when you need support-level detail.");
        ui.add_space(10.0);

        egui::Frame::group(ui.style()).show(ui, |ui| {
            ui.strong("Recommended action");
            ui.add_space(4.0);
            ui.label(self.next_action());
            ui.add_space(8.0);
            self.readiness_strip(ui);
        });

        ui.add_space(12.0);
        egui::CollapsingHeader::new("Customer readiness receipt (JSON)")
            .default_open(false)
            .show(ui, |ui| {
                if let Some(value) = &self.readiness {
                    let mut text = serde_json::to_string_pretty(value).unwrap_or_else(|_| "{}".to_owned());
                    ui.add(egui::TextEdit::multiline(&mut text).font(egui::TextStyle::Monospace).desired_rows(14).interactive(false));
                } else if let Some(err) = &self.readiness_error {
                    ui.label(err);
                } else {
                    ui.label("Readiness receipt unavailable.");
                }
            });

        egui::CollapsingHeader::new("Doctor report (JSON)")
            .default_open(false)
            .show(ui, |ui| {
                if let Some(value) = &self.doctor {
                    let mut text = serde_json::to_string_pretty(value).unwrap_or_else(|_| "{}".to_owned());
                    ui.add(egui::TextEdit::multiline(&mut text).font(egui::TextStyle::Monospace).desired_rows(18).interactive(false));
                } else if let Some(err) = &self.doctor_error {
                    ui.label(err);
                } else {
                    ui.label("Diagnostics unavailable.");
                }
            });
    }
}

impl eframe::App for GremlinControlCenter {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        Self::configure_style(ctx);
        self.handle_dropped_files(ctx);

        egui::TopBottomPanel::top("top_bar").show(ctx, |ui| {
            ui.add_space(4.0);
            ui.horizontal_wrapped(|ui| {
                ui.strong(egui::RichText::new("GREMLIN").size(20.0));
                ui.label("AI Research Orchestrator");
                ui.separator();
                ui.label(self.platform_name());
                ui.separator();
                Self::status_label(ui, self.ready_status());
            });
            ui.add_space(4.0);
        });

        egui::SidePanel::left("navigation")
            .resizable(false)
            .default_width(180.0)
            .show(ctx, |ui| {
                ui.add_space(10.0);
                ui.strong("CONTROL CENTER");
                ui.add_space(10.0);
                self.nav(ui);
            });

        egui::CentralPanel::default().show(ctx, |ui| {
            egui::ScrollArea::vertical()
                .auto_shrink([false, false])
                .show(ui, |ui| {
                    ui.set_max_width(1100.0);
                    ui.add_space(8.0);
                    match self.tab {
                        Tab::Setup => self.setup(ui),
                        Tab::Overview => self.overview(ui),
                        Tab::License => self.license(ui),
                        Tab::Integrations => self.integrations(ui),
                        Tab::Settings => self.settings(ui),
                        Tab::Diagnostics => self.diagnostics(ui),
                    }
                    ui.add_space(24.0);
                });
        });
    }
}

fn main() -> eframe::Result<()> {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1180.0, 820.0])
            .with_min_inner_size([900.0, 640.0]),
        ..Default::default()
    };
    eframe::run_native(
        "GREMLIN Control Center",
        options,
        Box::new(|_cc| Ok(Box::<GremlinControlCenter>::default())),
    )
}