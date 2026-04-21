import { useEffect, useState } from 'react';
import {
  Button,
  Form,
  Input,
  InputNumber,
  message,
  Modal,
  Space,
  Table,
  Tag,
  Typography
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { createScenario, fetchScenarios } from '../api/scenarios';
import type { Scenario } from '../types';

const { Text } = Typography;

const DEFAULT_CENTER_LNG = 116.3544;
const DEFAULT_CENTER_LAT = 39.9883;

export default function ScenarioPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [selectedId, setSelectedId] = useState(
    localStorage.getItem('activeScenarioId') || ''
  );

  const loadScenarios = async () => {
    setLoading(true);
    try {
      const data = await fetchScenarios();
      setScenarios(data);
      if (!selectedId && data.length > 0) {
        applySelection(data[0]);
      }
    } catch (error) {
      message.error('Failed to load scenarios');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadScenarios();
  }, []);

  const applySelection = (scenario: Scenario) => {
    setSelectedId(scenario.id);
    localStorage.setItem('activeScenarioId', scenario.id);
    localStorage.setItem(
      'activeScenarioCenter',
      JSON.stringify([scenario.centerLng, scenario.centerLat])
    );
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      await createScenario(values);
      message.success('Scenario created');
      setModalOpen(false);
      form.resetFields();
      loadScenarios();
    } catch (error) {
      if (String(error).includes('validate')) {
        return;
      }
      message.error('Failed to create scenario');
    }
  };

  const handleSelect = (scenario: Scenario) => {
    applySelection(scenario);
    message.success(`Selected: ${scenario.name}`);
  };

  const columns: ColumnsType<Scenario> = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (_, record) => (
        <Space>
          <Text strong>{record.name}</Text>
          {record.id === selectedId ? <Tag color="green">Active</Tag> : null}
        </Space>
      )
    },
    {
      title: 'Description',
      dataIndex: 'description',
      key: 'description'
    },
    {
      title: 'Center (lng, lat)',
      key: 'center',
      render: (_, record) =>
        `${record.centerLng?.toFixed(4) ?? '--'}, ${record.centerLat?.toFixed(4) ?? '--'}`
    },
    {
      title: 'Created',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: value => new Date(value).toLocaleString()
    },
    {
      title: 'Action',
      key: 'action',
      render: (_, record) => (
        <Button
          size="small"
          type={record.id === selectedId ? 'default' : 'primary'}
          onClick={() => handleSelect(record)}
        >
          {record.id === selectedId ? 'Selected' : 'Select'}
        </Button>
      )
    }
  ];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Scenario Management</h2>
          <Text type="secondary">Create and select a scenario for simulation.</Text>
        </div>
        <Button type="primary" onClick={() => setModalOpen(true)}>
          New Scenario
        </Button>
      </div>

      <Table
        rowKey="id"
        loading={loading}
        columns={columns}
        dataSource={scenarios}
        pagination={false}
      />

      <Modal
        title="Create Scenario"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={handleCreate}
        okText="Create"
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            centerLng: DEFAULT_CENTER_LNG,
            centerLat: DEFAULT_CENTER_LAT
          }}
        >
          <Form.Item
            name="name"
            label="Scenario Name"
            rules={[{ required: true, message: 'Please enter a name' }]}
          >
            <Input placeholder="Demo scenario" />
          </Form.Item>
          <Form.Item name="description" label="Description">
            <Input.TextArea rows={3} placeholder="Short description" />
          </Form.Item>
          <Space size="large">
            <Form.Item
              name="centerLng"
              label="Center Longitude"
              rules={[{ required: true, message: 'Enter longitude' }]}
            >
              <InputNumber min={-180} max={180} step={0.0001} style={{ width: 180 }} />
            </Form.Item>
            <Form.Item
              name="centerLat"
              label="Center Latitude"
              rules={[{ required: true, message: 'Enter latitude' }]}
            >
              <InputNumber min={-90} max={90} step={0.0001} style={{ width: 180 }} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  );
}
