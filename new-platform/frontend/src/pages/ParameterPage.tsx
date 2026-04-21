import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Collapse,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  Upload,
  message
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { DownloadOutlined, PlusOutlined, UploadOutlined } from '@ant-design/icons';
import type { UploadProps } from 'antd';
import { fetchAlgorithms, startSimulation } from '../api/simulations';
import { fetchScenarios } from '../api/scenarios';
import type {
  AlgorithmOption,
  NodeData,
  NodeType,
  Scenario,
  SimulationRequest
} from '../types';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

type BasicForm = Pick<
  SimulationRequest,
  'scenarioId' | 'algorithmId' | 'totalSlots' | 'nodeCount' | 'areaSize' | 'speed'
>;

const NODE_GROUPS: { type: NodeType; label: string; prefix: string; defaultHeight: number }[] = [
  { type: 'UAV', label: 'UAV (无人机)', prefix: 'UAV', defaultHeight: 120 },
  { type: 'HAP', label: 'HAP (高空平台)', prefix: 'HAP', defaultHeight: 500 },
  { type: 'GROUND_STATION', label: 'Ground Station (地面站)', prefix: 'GS', defaultHeight: 0 },
  { type: 'TERMINAL', label: 'Terminal (终端)', prefix: 'TERM', defaultHeight: 1.5 }
];

const DEFAULT_CENTER: [number, number] = [116.3544, 39.9883];

function readStoredCenter(): [number, number] {
  try {
    const raw = localStorage.getItem('activeScenarioCenter');
    if (!raw) return DEFAULT_CENTER;
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length === 2) {
      const lng = Number(parsed[0]);
      const lat = Number(parsed[1]);
      if (Number.isFinite(lng) && Number.isFinite(lat)) return [lng, lat];
    }
  } catch {
    // ignore
  }
  return DEFAULT_CENTER;
}

// JSON payload aligned with original system's stationAddImport.json style
// (pnId / pnType / longitude / latitude), plus a height field for altitude.
interface PhysicalNodeRecord {
  pnId: string;
  pnType: string;
  longitude: string | number;
  latitude: string | number;
  height?: string | number;
}

function toPhysicalNodeRecord(node: NodeData): PhysicalNodeRecord {
  return {
    pnId: node.id,
    pnType: node.type,
    longitude: node.lng,
    latitude: node.lat,
    height: node.height
  };
}

function buildTemplate(center: [number, number]): { physicalNodeList: PhysicalNodeRecord[] } {
  const [lng, lat] = center;
  const sample: NodeData[] = [
    { id: 'UAV-0', type: 'UAV', lng, lat, height: 120 },
    { id: 'UAV-1', type: 'UAV', lng: lng + 0.003, lat: lat + 0.002, height: 120 },
    { id: 'HAP-0', type: 'HAP', lng: lng - 0.004, lat: lat - 0.002, height: 500 },
    { id: 'GS-0', type: 'GROUND_STATION', lng, lat, height: 0 },
    { id: 'TERM-0', type: 'TERMINAL', lng: lng + 0.001, lat: lat - 0.001, height: 1.5 }
  ];
  return { physicalNodeList: sample.map(toPhysicalNodeRecord) };
}

// Aliases from the original system's node taxonomy (see nodeType.json /
// AmapPage terminal types / bsType in base-station imports) collapsed
// into our four canonical types.
const TYPE_ALIASES: Record<string, NodeType> = {
  UAV: 'UAV',
  DRONE: 'UAV',
  TESTUAV: 'UAV',

  HAP: 'HAP',
  HAPS: 'HAP',
  BALLOON: 'HAP',

  GROUND_STATION: 'GROUND_STATION',
  GROUNDSTATION: 'GROUND_STATION',
  GS: 'GROUND_STATION',
  GATEWAYSTATION: 'GROUND_STATION',
  BASESTATION: 'GROUND_STATION',
  BS: 'GROUND_STATION',
  VSWITCH: 'GROUND_STATION',
  ROUTER: 'GROUND_STATION',

  TERMINAL: 'TERMINAL',
  MOBILE: 'TERMINAL',
  MULTIMODE: 'TERMINAL',
  MT: 'TERMINAL',
  BT: 'TERMINAL',
  CS: 'TERMINAL',
  BROADBANDTERMINAL: 'TERMINAL',
  MOBILETERMINAL: 'TERMINAL',
  CLIENTSATELLITE: 'TERMINAL'
};

function normalizePnType(raw: unknown): NodeType | null {
  if (typeof raw !== 'string') return null;
  const key = raw.trim().toUpperCase();
  return TYPE_ALIASES[key] ?? null;
}

function parseNumericField(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) return v;
  if (typeof v === 'string') {
    const n = Number(v.trim());
    return Number.isFinite(n) ? n : null;
  }
  return null;
}

function parseImportedJson(
  raw: string
): { ok: true; nodes: NodeData[]; skipped: number; skippedTypes: string[] } | { ok: false; error: string } {
  let parsed: any;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    return { ok: false, error: 'Invalid JSON' };
  }

  const list: unknown = Array.isArray(parsed)
    ? parsed
    : Array.isArray(parsed?.physicalNodeList)
      ? parsed.physicalNodeList
      : Array.isArray(parsed?.nodes)
        ? parsed.nodes
        : null;

  if (!list) {
    return { ok: false, error: 'Missing physicalNodeList or nodes array' };
  }

  const out: NodeData[] = [];
  let skipped = 0;
  const skippedTypeSet = new Set<string>();
  for (let i = 0; i < (list as any[]).length; i++) {
    const item = (list as any[])[i];
    if (!item || typeof item !== 'object') {
      skipped++;
      continue;
    }
    const rawType = item.pnType ?? item.type ?? item.bsType ?? item.nodeType;
    const type = normalizePnType(rawType);
    if (!type) {
      skipped++;
      if (typeof rawType === 'string') skippedTypeSet.add(rawType);
      continue;
    }
    const lng = parseNumericField(item.longitude ?? item.lng);
    const lat = parseNumericField(item.latitude ?? item.lat);
    const height = parseNumericField(item.height ?? item.altitude);
    if (lng === null || lat === null) {
      skipped++;
      continue;
    }
    const id = String(item.pnId ?? item.id ?? item.bsId ?? item.nodeId ?? `${type}-${i}`);
    const name = typeof (item.bsName ?? item.name) === 'string'
      ? String(item.bsName ?? item.name)
      : undefined;
    out.push({
      id,
      type,
      lng,
      lat,
      height: height ?? defaultHeightFor(type),
      ...(name ? { name } : {})
    });
  }

  if (out.length === 0) {
    const hint = skippedTypeSet.size > 0
      ? ` (unrecognized types: ${[...skippedTypeSet].join(', ')})`
      : '';
    return { ok: false, error: `No valid nodes recognized${hint}` };
  }
  return { ok: true, nodes: out, skipped, skippedTypes: [...skippedTypeSet] };
}

function defaultHeightFor(type: NodeType): number {
  return NODE_GROUPS.find(g => g.type === type)?.defaultHeight ?? 0;
}

function downloadBlob(filename: string, content: string) {
  const blob = new Blob([content], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 0);
}

export default function ParameterPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [algorithms, setAlgorithms] = useState<AlgorithmOption[]>([]);
  const [loading, setLoading] = useState(false);
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [form] = Form.useForm<BasicForm>();
  const navigate = useNavigate();

  const center = useMemo<[number, number]>(() => readStoredCenter(), []);

  useEffect(() => {
    const loadOptions = async () => {
      try {
        const [scenarioData, algorithmData] = await Promise.all([
          fetchScenarios(),
          fetchAlgorithms()
        ]);
        setScenarios(scenarioData);
        setAlgorithms(algorithmData);

        const activeScenarioId = localStorage.getItem('activeScenarioId');
        if (activeScenarioId) {
          form.setFieldsValue({ scenarioId: activeScenarioId } as BasicForm);
        } else if (scenarioData.length > 0) {
          form.setFieldsValue({ scenarioId: scenarioData[0].id } as BasicForm);
        }

        if (algorithmData.length > 0) {
          form.setFieldsValue({ algorithmId: algorithmData[0].id } as BasicForm);
        }
      } catch (error) {
        message.error('Failed to load options');
      }
    };

    loadOptions();
  }, [form]);

  const addNode = (type: NodeType) => {
    const group = NODE_GROUPS.find(g => g.type === type)!;
    const existing = nodes.filter(n => n.type === type);
    const id = `${group.prefix}-${existing.length}`;
    const jitter = existing.length * 0.0005;
    setNodes(prev => [
      ...prev,
      {
        id,
        type,
        lng: center[0] + jitter,
        lat: center[1] + jitter,
        height: group.defaultHeight
      }
    ]);
  };

  const updateNode = (id: string, patch: Partial<NodeData>) => {
    setNodes(prev => prev.map(n => (n.id === id ? { ...n, ...patch } : n)));
  };

  const removeNode = (id: string) => {
    setNodes(prev => prev.filter(n => n.id !== id));
  };

  const clearAll = () => setNodes([]);

  const handleDownloadTemplate = () => {
    downloadBlob('node-import-template.json', JSON.stringify(buildTemplate(center), null, 2));
  };

  const handleExportCurrent = () => {
    if (nodes.length === 0) {
      message.info('No nodes to export');
      return;
    }
    downloadBlob(
      'node-list.json',
      JSON.stringify({ physicalNodeList: nodes.map(toPhysicalNodeRecord) }, null, 2)
    );
  };

  const uploadProps: UploadProps = {
    accept: '.json,application/json',
    beforeUpload: file => {
      const reader = new FileReader();
      reader.onload = e => {
        const raw = typeof e.target?.result === 'string' ? e.target.result : '';
        const result = parseImportedJson(raw);
        if (!result.ok) {
          message.error(`Import failed: ${result.error}`);
          return;
        }
        const existingIds = new Set(nodes.map(n => n.id));
        const added: NodeData[] = [];
        const duplicateIds: string[] = [];
        for (const node of result.nodes) {
          if (existingIds.has(node.id)) {
            duplicateIds.push(node.id);
          } else {
            added.push(node);
            existingIds.add(node.id);
          }
        }
        setNodes(prev => [...prev, ...added]);

        const parts: string[] = [`Imported ${added.length} nodes`];
        if (duplicateIds.length > 0) parts.push(`skipped ${duplicateIds.length} duplicate id`);
        if (result.skipped > 0) {
          const typeHint = result.skippedTypes.length > 0
            ? ` (unknown types: ${result.skippedTypes.join(', ')})`
            : '';
          parts.push(`skipped ${result.skipped} invalid${typeHint}`);
        }
        if (duplicateIds.length > 0 || result.skipped > 0 || added.length === 0) {
          message.warning(parts.join(' · '));
        } else {
          message.success(parts[0]);
        }
      };
      reader.onerror = () => message.error('Failed to read file');
      reader.readAsText(file);
      return false; // stop antd auto-upload
    },
    showUploadList: false
  };

  const nodeColumns: ColumnsType<NodeData> = [
    {
      title: 'pnId',
      dataIndex: 'id',
      width: 160,
      render: (_, record) => (
        <Input
          value={record.id}
          onChange={e => updateNode(record.id, { id: e.target.value })}
        />
      )
    },
    {
      title: 'Longitude',
      dataIndex: 'lng',
      width: 180,
      render: (_, record) => (
        <InputNumber
          value={record.lng}
          min={-180}
          max={180}
          step={0.0001}
          style={{ width: '100%' }}
          onChange={value => updateNode(record.id, { lng: Number(value ?? 0) })}
        />
      )
    },
    {
      title: 'Latitude',
      dataIndex: 'lat',
      width: 180,
      render: (_, record) => (
        <InputNumber
          value={record.lat}
          min={-90}
          max={90}
          step={0.0001}
          style={{ width: '100%' }}
          onChange={value => updateNode(record.id, { lat: Number(value ?? 0) })}
        />
      )
    },
    {
      title: 'Height (m)',
      dataIndex: 'height',
      width: 140,
      render: (_, record) => (
        <InputNumber
          value={record.height}
          min={0}
          step={10}
          style={{ width: '100%' }}
          onChange={value => updateNode(record.id, { height: Number(value ?? 0) })}
        />
      )
    },
    {
      title: '',
      key: 'action',
      width: 80,
      render: (_, record) => (
        <Button size="small" danger onClick={() => removeNode(record.id)}>
          Delete
        </Button>
      )
    }
  ];

  const handleSubmit = async (values: BasicForm) => {
    setLoading(true);
    try {
      const payload: SimulationRequest = {
        ...values,
        ...(nodes.length > 0 ? { nodes } : {})
      };
      const result = await startSimulation(payload);
      message.success('Simulation started');
      navigate(`/simulation/${result.id}`);
    } catch (error) {
      message.error('Failed to start simulation');
    } finally {
      setLoading(false);
    }
  };

  const collapseItems = NODE_GROUPS.map(group => {
    const groupNodes = nodes.filter(n => n.type === group.type);
    return {
      key: group.type,
      label: (
        <Space>
          <Text strong>{group.label}</Text>
          <Tag color="blue">{groupNodes.length}</Tag>
        </Space>
      ),
      children: (
        <>
          <Table
            size="small"
            rowKey="id"
            pagination={false}
            columns={nodeColumns}
            dataSource={groupNodes}
            locale={{ emptyText: 'No nodes — click Add to start' }}
          />
          <Button
            type="dashed"
            icon={<PlusOutlined />}
            onClick={() => addNode(group.type)}
            style={{ marginTop: 12 }}
          >
            Add {group.label}
          </Button>
        </>
      )
    };
  });

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Parameter Input</h2>
          <Text type="secondary">Configure algorithm parameters and, optionally, an explicit node list.</Text>
        </div>
      </div>

      {scenarios.length === 0 ? (
        <Alert
          type="warning"
          message="No scenarios available"
          description="Create a scenario first, then return here to start simulation."
          showIcon
        />
      ) : (
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            totalSlots: 30,
            nodeCount: 12,
            areaSize: 400,
            speed: 1
          }}
        >
          <Form.Item
            name="scenarioId"
            label="Scenario"
            rules={[{ required: true, message: 'Select a scenario' }]}
          >
            <Select
              options={scenarios.map(item => ({ value: item.id, label: item.name }))}
            />
          </Form.Item>

          <Form.Item
            name="algorithmId"
            label="Algorithm"
            rules={[{ required: true, message: 'Select an algorithm' }]}
          >
            <Select
              options={algorithms.map(item => ({ value: item.id, label: item.name }))}
            />
          </Form.Item>

          <Space size="large" className="form-row" wrap>
            <Form.Item
              name="totalSlots"
              label="Total Slots"
              rules={[{ required: true, message: 'Enter total slots' }]}
            >
              <InputNumber min={10} max={300} />
            </Form.Item>
            <Form.Item
              name="nodeCount"
              label="Node Count (fallback generator)"
              rules={[{ required: true, message: 'Enter node count' }]}
            >
              <InputNumber min={3} max={100} />
            </Form.Item>
            <Form.Item
              name="areaSize"
              label="Area Size (m)"
              rules={[{ required: true, message: 'Enter area size' }]}
            >
              <InputNumber min={50} max={5000} />
            </Form.Item>
            <Form.Item
              name="speed"
              label="Speed"
              rules={[{ required: true, message: 'Enter speed' }]}
            >
              <InputNumber min={0.2} max={5} step={0.2} />
            </Form.Item>
          </Space>

          <div style={{ marginTop: 8, marginBottom: 8 }}>
            <Space wrap>
              <Text strong>Node Configuration</Text>
              <Text type="secondary">
                If the node list is non-empty, it overrides the algorithm's generated positions.
              </Text>
            </Space>
          </div>

          <Space wrap style={{ marginBottom: 12 }}>
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>Import JSON</Button>
            </Upload>
            <Button icon={<DownloadOutlined />} onClick={handleDownloadTemplate}>
              Download Template
            </Button>
            <Button onClick={handleExportCurrent}>Export Current</Button>
            <Popconfirm
              title="Clear all nodes?"
              onConfirm={clearAll}
              disabled={nodes.length === 0}
            >
              <Button danger disabled={nodes.length === 0}>
                Clear All
              </Button>
            </Popconfirm>
            <Text type="secondary">Total: {nodes.length}</Text>
          </Space>

          <Collapse items={collapseItems} defaultActiveKey={['UAV']} />

          <Form.Item style={{ marginTop: 16 }}>
            <Button type="primary" htmlType="submit" loading={loading}>
              Start Simulation
            </Button>
          </Form.Item>
        </Form>
      )}
    </div>
  );
}
