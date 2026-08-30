#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use eframe::egui;
use serde_json::Value;
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
}

impl Default for GremlinControlCenter {
    fn default() -> Self {
        let mut app = Self {
            tab: Tab::Overview,
            doctor: None,
            doctor_error: None,
        };
        app.refresh_doctor();
        app
    }
}

impl GremlinControlCenter {
    fn refresh_doctor(&mut self) {
        self.doctor = None;
        self.doctor_error = None;
        match Command::new("gremlinctl").args(["doctor", "--json"]).output() {
            Ok(output) => match serde_json::from_slice::<Value>(&output.stdout) {
                Ok(value) => self.doctor = Some(value),
                Err(err) => {
                    self.doctor_error = Some(format!("Could not decode gremlinctl diagnostics: {err}"));
                }
            },
            Err(err) => {
                self.doctor_error = Some(format!("Could not launch gremlinctl: {err}"));
            }
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
        egui::Grid::new("overview_status").num_columns(2).spacing([24.0, 12.0]).show(ui, |ui| {
            ui.label("System");
            ui.strong(self.overall_status());
            ui.end_row();
            ui.label("License");
            ui.strong(self.product_status());
            ui.end_row();
            ui.label("MCP transport");
            ui.strong(self.runtime_transport());
            ui.end_row();
        });
        ui.add_space(16.0);
        if ui.button("Run diagnostics").clicked() {
            self.refresh_doctor();
        }
        if let Some(err) = &self.doctor_error {
            ui.add_space(8.0);
            ui.label(err);
        }
    }

    fn license(&mut self, ui: &mut egui::Ui) {
        ui.heading("License");
        ui.label(format!("Current status: {}", self.product_status()));
        ui.add_space(8.0);
        ui.label("Activation, offline license import and device certificates are the next product milestone.");
    }

    fn integrations(&mut self, ui: &mut egui::Ui) {
        ui.heading("MCP integrations");
        ui.label("The integration adapter layer will discover supported AI clients, patch their MCP config atomically and verify the handshake.");
        ui.add_space(8.0);
        ui.label("Generic MCP configuration remains available as the fallback path.");
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
