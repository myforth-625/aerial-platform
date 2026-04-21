package com.aerialplatform.bo;

import com.aerialplatform.dao.*;
import com.aerialplatform.po.*;
import com.aerialplatform.bo.TestUAVNodeEntity;
import com.aerialplatform.utils.GeneralConstants;
import com.aerialplatform.utils.Logger;
import com.aerialplatform.vo.LinkVO;
import com.aerialplatform.vo.PortVO;
import com.aerialplatform.vo.WirelessLinkVO;
import com.fasterxml.jackson.core.type.TypeReference;
import com.bupt.utils.GetBeanUtil;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.SerializationFeature;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.stereotype.Component;

import java.io.BufferedWriter;
import java.io.File;
import java.io.IOException;
import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.function.LongSupplier;

@Component
public class MaddpgAlgorithmEntity extends AlgorithmEntity {

    private static final ObjectMapper MAPPER = new ObjectMapper()
            .enable(SerializationFeature.INDENT_OUTPUT) // 漂亮打印
            .disable(SerializationFeature.FAIL_ON_EMPTY_BEANS)
            .registerModule(new JavaTimeModule()) // 支持 LocalDateTime 等
            .disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

    // 对算法进行计时用
    /** 每个场景一份明细缓存 */
    private final Map<Integer, List<WorkStageTime>> scenario2Records = new HashMap<>();

    /** 一行明细 */
    private static class WorkStageTime {
        long timeSlot;
        long saveCostMs; // 保存文件阶段
        long algCostMs; // 调用算法阶段
        long handleCostMs; // 处理输出阶段

        long totalMs() {
            return saveCostMs + algCostMs + handleCostMs;
        }
    }

    // 文件保存的基础路径,算法文件也保存在此文件夹下
    //private static final String baseFilePath="D:/work/Algorithm";
    private static final String baseFilePath ="C:/Users/admin/Desktop/Algorithm";
//    private static final String baseFilePath = System.getProperty("user.home") + "/Desktop/Algorithm";

    @Override
    public boolean create(Map<String, String> createInfo) {// 算法节点创建时执行
        // 如果是已存在类型的算法，creat函数仅执行这一行代码即可

        // 本算法是原有架构中不存在类型的算法，因此算法的creat函数需要设置算法的id
        // ，运行周期，初始化优先级，运行优先级，后处理优先级等基础属性
        createInfo.put("id", "justForStudyAlgorithmEntity");
        createInfo.put("period", "1");
        createInfo.put("runPriority", "14");
        createInfo.put("initPriority", "14");
        createInfo.put("postProcessPriority", "14");
        super.create(createInfo);
        // 控制台打印信息
        Logger.i("创建可挂载对象 ~ class: " + this.getClass().getSimpleName() +
                ", id: " + id, 2);
        return true;
    }

    @Override
    public void initialize() {// 初始化时执行
        super.initialize();
        Logger.i("执行初始化 ~ class: " + this.getClass().getSimpleName(), 2);
    }

    @Override
    public void runWorkSlot(long currentTimeSlot) {
        if (currentTimeSlot % 10 == 0) {// 目前每10周期调用一次算法
            work(currentTimeSlot);
        }
        super.runWorkSlot(currentTimeSlot);
        Logger.i("aerialLinkAlgorithm runWorkSlot for fun!", 2);
    }

    public void work(long currentTimeSlot) {// 工作时间片执行
        /*
         * ------------------------------------- 阶段1：保存文件
         * -----------------------------------------------------
         */
        super.runWorkSlot(currentTimeSlot);
        Logger.i("执行时间片任务 ~ class: " + this.getClass().getSimpleName() +
                ", id: " + id, 2);
        // 获取拓扑管理模块，可以通过拓扑管理模块获取当前时刻的所有仿真信息
        SimTopo simTopo = GetBeanUtil.getBean(SimTopo.class);
        // 1.将算法所需要的数据保存到本地磁盘，本算法以保存上个时间片的所有快照数据为例
        Integer scenarioId = AerialScenarioInitParameterSingleton.get().getScenarioId();// 获取当前仿真场景id
        long t1 = System.nanoTime();
        saveSnapshotAsFile(baseFilePath, scenarioId, currentTimeSlot - 1);// 调用此方法保存上个时间片的快照
        long saveCost = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - t1);

        /*
         * ------------------------------------- 阶段2：调用算法
         * -------------------------------------------------------
         */
        long t2 = System.nanoTime();
        // 2.在此处调用你的算法，算法以1中保存的文件为输入并产生输出，比如可以把输出的结果保存在同文件夹下的output.json中
        Path workDir = Paths.get(baseFilePath, String.valueOf(scenarioId), String.valueOf(currentTimeSlot - 1));
        // 检查是否启用Python推理（通过环境变量控制，默认启用）
        String enableInference = System.getenv().getOrDefault("MADDPG_ENABLE_INFERENCE", "true");
        if ("true".equalsIgnoreCase(enableInference)) {
            Logger.i("启用Python推理功能", 2);
            callPythonInference(workDir);
        } else {
            Logger.i("Python推理功能已禁用，跳过推理步骤（如需启用，请设置环境变量 MADDPG_ENABLE_INFERENCE=true）", 2);
        }
        long algCost = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - t2);

        // 3.处理上一步骤算法的产生的输出。目前逻辑是仅仅在第一个时间片工作一次
        /*
         * ------------------------------------- 阶段3：处理算法输出
         * ---------------------------------------------------
         */
        long t3 = System.nanoTime();
        Logger.i("开始处理算法产生的输出", 2);

        // 3.1演示如何读取aerialNodeResult.json文件并处理输出
        Path aerialNodePath = workDir.resolve("aerialNodeResult.json");
        // 通过拓扑管理模块获取到所有的空中节点信息
        List<AerialNodeEntity> aerialNodeEntities = simTopo.getAerialNodeEntities();
        // 构造id-空中节点映射表，方便后续查找对应id的节点
        Map<String, AerialNodeEntity> aerialNodeMap = new HashMap<>();
        for (AerialNodeEntity entity : aerialNodeEntities) {
            aerialNodeMap.put(entity.getId(), entity);
        }
        try {
            List<AerialNode> aerialNodeResults = MAPPER.readValue(
                    aerialNodePath.toFile(),
                    new TypeReference<List<AerialNode>>() {
                    });
            Logger.i("成功读取 aerialNodeResult.json", 2);
            for (AerialNode result : aerialNodeResults) {
                // 遍历空中节点信息，找到我们要修改的节点并修改节点的属性
                AerialNodeEntity node = aerialNodeMap.get(result.getId());
                if (node != null && node instanceof TestUAVNodeEntity) {
                    TestUAVNodeEntity target = (TestUAVNodeEntity) node;
                    target.setTargetAltitude(new Double(result.getAltitude()));// 设置目标高度
                    target.setTargetLatitude(new BigDecimal(result.getLatitude()));// 设置目标纬度
                    target.setTargetLongitude(new BigDecimal(result.getLongitude()));// 设置目标经度
                } else if (node == null) {
                    Logger.w("没有这样的nodeid" + result.getId(), 2);
                } else {
                    Logger.i("跳过非 TestUAVNodeEntity 类型的节点，id: " + result.getId(), 2);
                    String fileName = "fail-" + scenarioId + "-" + node.getId() + ".txt";
                    writeJson(workDir, fileName, node.getId());
                }
            }
        } catch (IOException e) {
            Logger.i("读取 aerialNodeResult 失败", 2);
            e.printStackTrace();
        }
        // //3.2演示如何读取aerialWirelessLinkResult.json文件并处理输出
        // Path aerialWirelessLinkPath =
        // workDir.resolve("aerialWirelessLinkResult.json");
        // //通过拓扑管理模块获取到所有的无线链路信息
        // List<WirelessLinkVO> aerialLinkVOs = simTopo.getAerialLinkVOs();
        // //构造id-无线链路信息映射表，方便后续处理
        // Map<String,WirelessLinkVO> aerialLinkMap=new HashMap<>();
        // for(WirelessLinkVO entity:aerialLinkVOs){
        //// entity.setCurrentTimeSlot(currentTimeSlot);
        // aerialLinkMap.put(entity.getId(),entity);
        // }
        // try {
        // List<AerialWirelessLink> aerialWirelessResults=MAPPER.readValue(
        // aerialWirelessLinkPath.toFile(),
        // new TypeReference<List<AerialWirelessLink>>() {});
        // Logger.i("成功读取 aerialWirelessLinkResult.json", 2);
        // for(AerialWirelessLink result:aerialWirelessResults){
        // //遍历链路信息，找到要修改的链路id并修改对应属性
        // WirelessLinkVO link=aerialLinkMap.get(result.getId());
        // if (link != null) {//空值保护
        // link.setMaxDataCanTransfer(new
        // Double(result.getExtra().get("wlMaxDataCanTransfer").toString()));
        //// AerialNodeEntity newNode1=aerialNodeMap.get(result.getNodeId1());
        //// AerialNodeEntity newNode2=aerialNodeMap.get(result.getNodeId2());
        //// link.setNode1(newNode1);
        //// link.setNode2(newNode2);
        //// PortVO newPort1 = newNode1.getWirelessPortVOs().get(0);
        //// PortVO newPort2 = newNode2.getWirelessPortVOs().get(0);
        //// link.setPort1(newPort1);
        //// link.setPort2(newPort2);
        //// } else {
        //// Logger.w("没有这样的 wirelesslinkid: " + result.getId(), 2);
        //// }
        ////
        //// }
        //// } catch (IOException e) {
        //// Logger.i("读取 aerialWirelessLinkResult.json 失败", 2);
        //// e.printStackTrace();
        //// }
        // 下面是计时逻辑
        long handleCost = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - t3);
        /* ---------- 记录work函数花费的时间 ---------- */
        WorkStageTime record = new WorkStageTime();
        record.timeSlot = currentTimeSlot;
        record.saveCostMs = saveCost;
        record.algCostMs = algCost;
        record.handleCostMs = handleCost;

        scenario2Records.computeIfAbsent(scenarioId, k -> new ArrayList<>()).add(record);

        /* ---------- 实时写盘 ---------- */
        appendDetailToFile(baseFilePath, scenarioId, record);
    }

    // 计时用
    private void appendDetailToFile(String dir, int scenarioId, WorkStageTime r) {
        Path p = Paths.get(dir, scenarioId + "_worktime.csv");
        boolean header = !Files.exists(p);
        try (BufferedWriter w = Files.newBufferedWriter(p, StandardCharsets.UTF_8,
                StandardOpenOption.CREATE, StandardOpenOption.APPEND)) {
            if (header) {
                w.write("timeSlot,saveMs,algMs,handleMs,totalMs");
                w.newLine();
            }
            w.write(String.format("%d,%d,%d,%d,%d",
                    r.timeSlot, r.saveCostMs, r.algCostMs, r.handleCostMs, r.totalMs()));
            w.newLine();
        } catch (IOException e) {
            Logger.e("写计时文件失败: " + p, 2);
            e.printStackTrace();
        }
    }

    // 把某个仿真的某个时间片的快照以文件的形式保存在baseFilePath目录下
    public void saveSnapshotAsFile(String baseFilePath, Integer scenarioId, long timeSlot) {
        // 创建文件夹{baseFilePath}/{scenarioId}/{currentTimeSlot-1}/，此时间片所有文件都会保存在这个文件夹下面
        Path workDir = Paths.get(baseFilePath, String.valueOf(scenarioId), String.valueOf(timeSlot));
        try {
            Files.createDirectories(workDir);
        } catch (IOException e) {
            Logger.i("创建目录失败：" + workDir, 2);
            e.printStackTrace();
            return;
        }
        // ---------------------------------开始保存上一个时间片的快照文件-----------------------------------
        // 空中节点快照，保存为aerialNode.json
        AerialNodeMapper aerialNodeMapper = GetBeanUtil.getBean(AerialNodeMapper.class);
        List<AerialNode> aerialNodes = aerialNodeMapper.selectByTimeSlotInScenario(
                scenarioId, timeSlot);
        writeJson(workDir, "aerialNode.json", aerialNodes);

        // 空中链路快照，保存为aerialWirelessLink.json
        AerialWirelessLinkMapper aerialWirelessLinkMapper = GetBeanUtil.getBean(AerialWirelessLinkMapper.class);
        List<AerialWirelessLink> aerialWirelessLinks = aerialWirelessLinkMapper.selectByTimeSlotInScenario(
                scenarioId, timeSlot);
        writeJson(workDir, "aerialWirelessLink.json", aerialWirelessLinks);

        // 终端快照，保存为terminalSnapshot.json
        TerminalSnapshotMapper terminalSnapshotMapper = GetBeanUtil.getBean(TerminalSnapshotMapper.class);
        List<TerminalSnapshot> terminalSnapshots = terminalSnapshotMapper.selectByTimeSlotInScenario(
                scenarioId, timeSlot);
        writeJson(workDir, "terminalSnapshot.json", terminalSnapshots);

        // 地面节点快照，保存为groundNode.json
        GroundNodeMapper groundNodeMapper = GetBeanUtil.getBean(GroundNodeMapper.class);
        List<GroundNode> groundNodes = groundNodeMapper.selectByTimeSlotInScenario(
                scenarioId, timeSlot);
        writeJson(workDir, "groundNode.json", groundNodes);

        // 波束快照，保存为waveBeam.json
        WaveBeamMapper waveBeamMapper = GetBeanUtil.getBean(WaveBeamMapper.class);
        List<WaveBeam> waveBeams = waveBeamMapper.selectByTimeSlotInScenario(
                scenarioId, timeSlot);
        writeJson(workDir, "waveBeam.json", waveBeams);

        // 热力图快照，保存为heatMap.json
        ExtensibleSnapshotInfoMapper extensibleSnapshotInfoMapper = GetBeanUtil
                .getBean(ExtensibleSnapshotInfoMapper.class);
        List<ExtensibleSnapshotInfo> testAerialNodeHeatMapItem = extensibleSnapshotInfoMapper
                .selectAllExtensibleSnapshotInfo(
                        scenarioId, timeSlot, "TestAerialNodeHeatMapItem");
        writeJson(workDir, "heatMap.json", testAerialNodeHeatMapItem);

        // 协作簇快照，保存为apCluster.json
        List<ExtensibleSnapshotInfo> apClusterEntity = extensibleSnapshotInfoMapper.selectAllExtensibleSnapshotInfo(
                scenarioId, timeSlot, "APClusterEntity");
        writeJson(workDir, "apCluster.json", apClusterEntity);

        // 协作组快照，保存为apGroup.json
        List<ExtensibleSnapshotInfo> apGroupEntity = extensibleSnapshotInfoMapper.selectAllExtensibleSnapshotInfo(
                scenarioId, timeSlot, "APGroupEntity");
        writeJson(workDir, "apGroup.json", apGroupEntity);

        // 无线路由快照表的保存
        AerialLinkConnectionMapper linkConnectionMapper = GetBeanUtil.getBean(AerialLinkConnectionMapper.class);
        List<AerialLinkConnection> aerialLinkConnections = linkConnectionMapper.selectByTimeSlotInScenario(
                scenarioId, Long.valueOf(timeSlot));
        writeJson(workDir, "aerialLinkConnection.json", aerialLinkConnections);

        // 业务表的保存
        AerialServiceMapper aerialServiceMapper = GetBeanUtil.getBean(AerialServiceMapper.class);
        List<AerialService> aerialServices = aerialServiceMapper.selectByScenarioId(scenarioId);
        writeJson(workDir, "aerialService.json", aerialServices);
        // ---------------------------------上一个时间片的所有快照文件保存完毕-----------------------------------
    }

    // 保存文件的工具方法，输入参数分别为要保存的文件夹路径(要保存在哪个文件夹下)，文件名，要保存的数据
    public void writeJson(Path dir, String fileName, Object data) {
        File target = dir.resolve(fileName).toFile();
        try {
            MAPPER.writeValue(target, data);
        } catch (IOException e) {
            Logger.i("写文件失败：" + target, 2);
            e.printStackTrace();
        }
    }

    /**
     * 调用Python推理脚本
     *
     * @param workDir 工作目录，包含输入快照文件和输出结果文件
     */
    private void callPythonInference(Path workDir) {
        try {
            // 获取Python可执行文件和脚本路径（可通过环境变量配置）
            String pythonBin = System.getenv().getOrDefault("MADDPG_PYTHON_BIN", "python");
            String scriptPath = System.getenv().getOrDefault("MADDPG_INFERENCE_SCRIPT",
                    baseFilePath+"/maddpg_mAeBS-main/inference.py");
            String modelPath = System.getenv().getOrDefault("MADDPG_MODEL_PATH",
                    baseFilePath+"/maddpg_mAeBS-main/models");
            int steps = Integer.parseInt(System.getenv().getOrDefault("MADDPG_INFERENCE_STEPS", "100"));

            Logger.i("开始调用 MADDPG Python推理脚本", 2);
            Logger.i("  工作目录: " + workDir, 2);
            Logger.i("  Python可执行文件: " + pythonBin, 3);
            Logger.i("  脚本路径: " + scriptPath, 3);
            Logger.i("  模型路径: " + modelPath, 3);
            Logger.i("  优化步数: " + steps, 3);

            // 获取场景尺寸以进行自动缩放适配
            Double areaWidth = AerialScenarioInitParameterSingleton.get().getAreaWidth();
            Double areaHeight = AerialScenarioInitParameterSingleton.get().getAreaHeight();
            // 判空保护，如果为空默认使用6000
            if (areaWidth == null)
                areaWidth = 6000.0;
            if (areaHeight == null)
                areaHeight = 6000.0;

            // 获取参考坐标点（固定参考系）
            String refLon = System.getenv().getOrDefault("MADDPG_REF_LON", "116.355");
            String refLat = System.getenv().getOrDefault("MADDPG_REF_LAT", "39.962");
            Logger.i("  参考坐标: Lon " + refLon + ", Lat " + refLat, 3);
            Logger.i("  场景尺寸: " + areaWidth + "x" + areaHeight, 3);

            // 构建Python命令
            ProcessBuilder processBuilder = new ProcessBuilder(
                    pythonBin,
                    scriptPath, "--work_dir", workDir.toString(),
                    "--input_nodes", "aerialNode.json",
                    "--input_links", "aerialWirelessLink.json",
                    "--output_nodes", "aerialNodeResult.json",
                    "--output_links", "aerialWirelessLinkResult.json",
                    "--model_path", modelPath,
                    "--steps", String.valueOf(steps),
                    "--scene_width", String.valueOf(areaWidth),
                    "--scene_height", String.valueOf(areaHeight),
                    "--ref_lon", refLon,
                    "--ref_lat", refLat);

            // 设置工作目录为项目根目录（Python脚本的相对路径基于项目根目录）
            String projectRoot = System.getProperty("user.dir");
            processBuilder.directory(new File(projectRoot));
            Logger.i("  项目根目录: " + projectRoot, 3);

            // 合并标准输出和错误输出
            processBuilder.redirectErrorStream(true);

            // 启动进程
            Process process = processBuilder.start();

            // 读取输出（用于日志）- 使用线程分别读取stdout和stderr
            StringBuilder output = new StringBuilder();
            StringBuilder errorOutput = new StringBuilder();

            // 读取标准输出
            Thread stdoutReader = new Thread(() -> {
                try (java.io.BufferedReader reader = new java.io.BufferedReader(
                        new java.io.InputStreamReader(process.getInputStream(), "UTF-8"))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        synchronized (output) {
                            output.append(line).append("\n");
                        }
                        // 实时输出Python脚本的日志
                        Logger.i("Python: " + line, 2);
                    }
                } catch (IOException e) {
                    Logger.e("读取Python标准输出失败: " + e.getMessage(), 2);
                }
            });

            // 读取标准错误（虽然redirectErrorStream(true)，但为了保险还是读取）
            Thread stderrReader = new Thread(() -> {
                try (java.io.BufferedReader reader = new java.io.BufferedReader(
                        new java.io.InputStreamReader(process.getErrorStream(), "UTF-8"))) {
                    String line;
                    while ((line = reader.readLine()) != null) {
                        synchronized (errorOutput) {
                            errorOutput.append(line).append("\n");
                        }
                        Logger.e("Python错误: " + line, 2);
                    }
                } catch (IOException e) {
                    // 忽略，因为redirectErrorStream(true)时可能没有数据
                }
            });

            stdoutReader.start();
            stderrReader.start();

            // 等待进程完成，设置超时时间（默认5分钟）
            long timeoutSeconds = Long.parseLong(System.getenv().getOrDefault("SAC_INFERENCE_TIMEOUT", "300"));
            boolean finished = process.waitFor(timeoutSeconds, java.util.concurrent.TimeUnit.SECONDS);

            // 等待输出读取线程完成
            try {
                stdoutReader.join(5000); // 最多等待5秒
                stderrReader.join(5000);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }

            if (!finished) {
                process.destroyForcibly();
                Logger.e("Python推理脚本执行超时（" + timeoutSeconds + "秒）", 2);
                synchronized (output) {
                    Logger.e("Python输出: " + output.toString(), 2);
                }
                synchronized (errorOutput) {
                    if (errorOutput.length() > 0) {
                        Logger.e("Python错误输出: " + errorOutput.toString(), 2);
                    }
                }
                return;
            }

            int exitCode = process.exitValue();
            synchronized (output) {
                synchronized (errorOutput) {
                    String fullOutput = output.toString();
                    String fullError = errorOutput.toString();

                    if (exitCode != 0) {
                        Logger.e("Python推理脚本执行失败，退出码: " + exitCode, 2);
                        if (fullOutput.length() > 0) {
                            Logger.e("Python标准输出: " + fullOutput, 2);
                        }
                        if (fullError.length() > 0) {
                            Logger.e("Python错误输出: " + fullError, 2);
                        }
                        return;
                    } else {
                        // 即使成功也记录输出，方便调试
                        if (fullOutput.length() > 0) {
                            Logger.i("Python输出: " + fullOutput, 3);
                        }
                    }
                }
            }

            // 检查输出文件是否生成
            Path outputNodeFile = workDir.resolve("aerialNodeResult.json");
            Path outputLinkFile = workDir.resolve("aerialWirelessLinkResult.json");

            if (!Files.exists(outputNodeFile)) {
                Logger.w("警告: Python推理脚本未生成输出文件: " + outputNodeFile, 2);
            } else {
                Logger.i("Python推理完成，输出文件已生成: " + outputNodeFile, 2);
            }

            if (!Files.exists(outputLinkFile)) {
                Logger.w("警告: Python推理脚本未生成链路输出文件: " + outputLinkFile, 2);
            } else {
                Logger.i("Python推理完成，链路输出文件已生成: " + outputLinkFile, 2);
            }

        } catch (IOException e) {

            Thread.currentThread().interrupt();
        } catch (Exception e) {
            Logger.e("调用Python推理脚本时发生未知错误: " + e.getMessage(), 2);
            e.printStackTrace();
        }
    }

    @Override
    public List<SnapshotPO> output() {
        return super.output();

    }// 快照统一持久化时执行

    @Override
    public void postProcess() {
        super.postProcess();
    }// 后处理时执行

}
