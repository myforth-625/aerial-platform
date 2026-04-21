package com.minisim.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "inference")
public class InferenceProperties {
    private String pythonCommand = "python";
    private String scriptDir = "../maddpg_mAeBS-main";
    private String scriptName = "inference.py";
    private String modelPath = "models";
    private String workDir = "./target/inference-work";
    private int timeoutSeconds = 120;
    private boolean keepWorkDir = false;

    public String getPythonCommand() {
        return pythonCommand;
    }

    public void setPythonCommand(String pythonCommand) {
        this.pythonCommand = pythonCommand;
    }

    public String getScriptDir() {
        return scriptDir;
    }

    public void setScriptDir(String scriptDir) {
        this.scriptDir = scriptDir;
    }

    public String getScriptName() {
        return scriptName;
    }

    public void setScriptName(String scriptName) {
        this.scriptName = scriptName;
    }

    public String getModelPath() {
        return modelPath;
    }

    public void setModelPath(String modelPath) {
        this.modelPath = modelPath;
    }

    public String getWorkDir() {
        return workDir;
    }

    public void setWorkDir(String workDir) {
        this.workDir = workDir;
    }

    public int getTimeoutSeconds() {
        return timeoutSeconds;
    }

    public void setTimeoutSeconds(int timeoutSeconds) {
        this.timeoutSeconds = timeoutSeconds;
    }

    public boolean isKeepWorkDir() {
        return keepWorkDir;
    }

    public void setKeepWorkDir(boolean keepWorkDir) {
        this.keepWorkDir = keepWorkDir;
    }
}
