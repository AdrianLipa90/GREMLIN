#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use eframe::egui;
use serde_json::Value;
use std::path::PathBuf;
use std::process::Command;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Tab {
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
    integration_path: String,
    integration_result: Option<Value>,
    integration_error: Option<String>,
}

impl Default for GremlinControlCenter {
    fn default() -> Self {
        let mut app = Self {
            tab: Tab::Overview,
            doctor: None,
            doctor_error: None,
            device: None,
            device_error: None,
            integration_path: String::new(),
            integration_result: None,
            integration_error: None,
        };
        app.refresh_doctor();
        app.refresh_device();
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

fn run_ctl_json(args: &[String]) -> Result<Value, String> {
    let output = Command::new(ctl_program())
        .args(args)
        .output()
        .map_err(|err| format!("Could not launch gremlinctl: {err}"))?;
    if !output.status.success() && output.stdout.is_empty() {
        return Err(format!(
            "gremlinctl failed: {}",
            String::from_utf8_lossy(&output.stderr).trim()
        ));
    }
    serde_json::from_slice::<Value>(&output.stdout)
        .map_err(|err| format!("Could not decode gremlinctl JSON: {err}"))
}

impl GremlinControlCenter {
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

    fn initialize_device(&mut self) {
        self.device_error = None;
        match run_ctl_json(&["device".into(), "init".into(), "--json".into()]) {
            Ok(_value) => {
                self.refresh_device();
                self.refresh_doctor();
            }
            Err(err) => self.device_error = Some(err),
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
            "integrations".to_owned(),
            action.to_owned(),
            "--config".to_owned(),
            path.to_owned(),
            "--json".to_owned(),
        ];
        match run_ctl_json(&args) {
            Ok(value) => self.integration_result = Some(value),
            Err(err) => self.integration_error = Some(err),
        }
    }

    fn overall_status(&self) -> &str {
        self.doctor
            .as_ref()
            .and_then(|v| v.get("status"))
            .and_then(Value::as_str)
            .unwrap_or("UNAVAILABLE")
    }

    fn product_status(&self) -> &str {
        self.doctor
            .as_ref()
            .and_then(|v| v.get("product"))
            .and_then(|v| v.get("status"))
            .and_then(Value::as_str)
            .unwrap_or("NOT ACTIVATED")
    }

    fn device_status(&self) -> &str {
        self.device
            .as_ref()
            .and_then(|v| v.get("identity"))
            .and_then(|v| v.get("status"))
            .and_then(Value::as_str)
            .unwrap_or_else(|| {
                self.device
                    .as_ref()
                    .and_then(|v| v.get("status"))
                    .and_then(Value::as_str)
                    .unwrap_or("UNAVAILABLE")
            })
    }

    fn runtime_transport(&self) -> &str {
        self.doctor
            .as_ref()
            .and_then(|v| v.get("config"))
            .and_then(|v| v.get("runtime"))
            .and_then(|v| v.get("transport"))
            .and_then(Value::as_str)
            .unwrap_or("stdio")
    }

    fn nav(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.selectable_value(&mut self.tab, Tab::Overview, "Overview");
            ui.selectable_value(&mut self.tab, Tab::License, "License");
            ui.selectable_value(&mut self.tab, Tab::Integrations, "Integrations");
            ui.selectable_value(&mut self.tab, Tab::Settings, "Settings");
            ui.selectable_value(&mut self.tab, Tab::Diagnostics, "Diagnostics");
        });
    }

    fn overview(&mut self, ui: &mut egui::Ui) {
        ui.heading("GREMLIN AI Research Orchestrator");
        ui.add_space(8.0);
        egui::Grid::new("overview_status")
            .num_columns(2)
            .spacing([24.0, 12.0])
            .show(ui, |ui| {
                ui.label("System");
                ui.strong(self.overall_status());
                ui.end_row();
                ui.label("License");
                ui.strong(self.product_status());
                ui.end_row();
                ui.label("Device identity");
                ui.strong(self.device_status());
                ui.end_row();
                ui.label("MCP transport");
                ui.strong(self.runtime_transport());
                ui.end_row();
            });
        ui.add_space(16.0);
        if ui.button("Run diagnostics").clicked() {
            self.refresh_doctor();
            self.refresh_device();
        }
        if let Some(err) = &self.doctor_error {
            ui.add_space(8.0);
            ui.label(err);
        }
    }

    fn license(&mut self, ui: &mut egui::Ui) {
        ui.heading("License & device");
        ui.label(format!("Product entitlement: {}", self.product_status()));
        ui.label(format!("Device identity: {}", self.device_status()));
        if let Some(device_id) = self
            .device
            .as_ref()
            .and_then(|v| v.get("identity"))
            .and_then(|v| v.get("device_id"))
            .and_then(Value::as_str)
        {
            ui.label(format!("Device ID: {device_id}"));
        }
        ui.add_space(12.0);
        ui.horizontal(|ui| {
            if ui.button("Initialize device identity").clicked() {
                self.initialize_device();
            }
            if ui.button("Refresh").clicked() {
                self.refresh_device();
                self.refresh_doctor();
            }
        });
        if let Some(err) = &self.device_error {
            ui.add_space(8.0);
            ui.label(err);
        }
        ui.add_space(12.0);
        ui.label("Online activation and offline license import will consume this device identity without exposing its private key to the Control Center.");
    }

    fn integrations(&mut self, ui: &mut egui::Ui) {
        ui.heading("MCP integrations");
        ui.label("Generic JSON MCP integration fallback");
        ui.add_space(8.0);
        ui.horizontal(|ui| {
            ui.label("Config file");
            ui.text_edit_singleline(&mut self.integration_path);
        });
        ui.add_space(8.0);
        ui.horizontal(|ui| {
            if ui.button("Inspect").clicked() {
                self.integration_action("inspect");
            }
            if ui.button("Connect GREMLIN").clicked() {
                self.integration_action("install");
            }
            if ui.button("Remove GREMLIN").clicked() {
                self.integration_action("remove");
            }
        });
        if let Some(err) = &self.integration_error {
            ui.add_space(8.0);
            ui.label(err);
        }
        if let Some(result) = &self.integration_result {
            ui.add_space(8.0);
            let mut text = serde_json::to_string_pretty(result).unwrap_or_else(|_| "{}".to_owned());
            ui.add(
                egui::TextEdit::multiline(&mut text)
                    .font(egui::TextStyle::Monospace)
                    .desired_rows(12)
                    .interactive(false),
            );
        }
        ui.add_space(8.0);
        ui.label("Vendor-specific discovery adapters will feed detected config paths into the same backup/atomic-merge/verify backend.");
    }

    fn settings(&mut self, ui: &mut egui::Ui) {
        ui.heading("Settings");
        ui.label(format!("Effective transport: {}", self.runtime_transport()));
        ui.label("Settings are resolved by gremlinctl from the same cross-platform configuration contract used by installers.");
    }

    fn diagnostics(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.heading("Diagnostics");
            if ui.button("Refresh").clicked() {
                self.refresh_doctor();
                self.refresh_device();
            }
        });
        ui.separator();
        if let Some(value) = &self.doctor {
            let mut text = serde_json::to_string_pretty(value).unwrap_or_else(|_| "{}".to_owned());
            ui.add(
                egui::TextEdit::multiline(&mut text)
                    .font(egui::TextStyle::Monospace)
                    .desired_rows(24)
                    .interactive(false),
            );
        } else if let Some(err) = &self.doctor_error {
            ui.label(err);
        } else {
            ui.label("Diagnostics unavailable.");
        }
    }
}

impl eframe::App for GremlinControlCenter {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::TopBottomPanel::top("top_bar").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.strong("GREMLIN Control Center");
                ui.separator();
                ui.label(self.overall_status());
            });
            self.nav(ui);
        });

        egui::CentralPanel::default().show(ctx, |ui| match self.tab {
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
            .with_inner_size([920.0, 620.0])
            .with_min_inner_size([720.0, 480.0]),
        ..Default::default()
    };
    eframe::run_native(
        "GREMLIN Control Center",
        options,
        Box::new(|_cc| Ok(Box::<GremlinControlCenter>::default())),
    )
}
