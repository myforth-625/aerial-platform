import { useEffect, useMemo, useRef, useState } from 'react';
import { Button, Card, InputNumber, Slider, Space, Tag, Typography, message } from 'antd';
import { useParams } from 'react-router-dom';
import {
  fetchFrame,
  fetchSimulationState,
  pauseSimulation,
  resumeSimulation,
  stopSimulation
} from '../api/simulations';
import type { FrameData, SimulationState } from '../types';
import AmapScene from '../components/AmapScene';

const { Text } = Typography;

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
    // fallthrough to default
  }
  return DEFAULT_CENTER;
}

export default function SimulationPage() {
  const { id } = useParams<{ id: string }>();
  const [state, setState] = useState<SimulationState | null>(null);
  const [frame, setFrame] = useState<FrameData | null>(null);
  const [slot, setSlot] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [intervalMs, setIntervalMs] = useState(800);
  const timerRef = useRef<number | null>(null);

  const center = useMemo<[number, number]>(() => readStoredCenter(), []);

  const totalSlots = state?.totalSlots || 0;
  const maxSlot = Math.max(totalSlots - 1, 0);

  useEffect(() => {
    if (!id) return;

    const loadState = async () => {
      try {
        const data = await fetchSimulationState(id);
        setState(data);
        setSlot(data.currentSlot || 0);
        const initialFrame = await fetchFrame(id, data.currentSlot || 0);
        setFrame(initialFrame);
      } catch (error) {
        message.error('Failed to load simulation');
      }
    };

    loadState();
  }, [id]);

  useEffect(() => {
    if (!id) return;
    const loadFrame = async () => {
      try {
        const data = await fetchFrame(id, slot);
        setFrame(data);
      } catch (error) {
        message.error('Failed to load frame');
      }
    };

    loadFrame();
  }, [id, slot]);

  useEffect(() => {
    if (!isPlaying || !id) return;

    timerRef.current = window.setInterval(() => {
      setSlot(prev => {
        const next = prev + 1;
        if (next > maxSlot) {
          setIsPlaying(false);
          return prev;
        }
        return next;
      });
    }, intervalMs);

    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [isPlaying, intervalMs, maxSlot, id]);

  const handlePlay = async () => {
    if (!id) return;
    try {
      const updated = await resumeSimulation(id);
      setState(updated);
      setIsPlaying(true);
    } catch (error) {
      message.error('Failed to resume simulation');
    }
  };

  const handlePause = async () => {
    if (!id) return;
    try {
      const updated = await pauseSimulation(id);
      setState(updated);
      setIsPlaying(false);
    } catch (error) {
      message.error('Failed to pause simulation');
    }
  };

  const handleStop = async () => {
    if (!id) return;
    try {
      const updated = await stopSimulation(id);
      setState(updated);
      setIsPlaying(false);
      setSlot(0);
    } catch (error) {
      message.error('Failed to stop simulation');
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>Simulation View</h2>
          <Text type="secondary">Playback and inspect 3D frames.</Text>
        </div>
        <Space>
          <Tag color={state?.status === 'RUNNING' ? 'green' : 'default'}>
            {state?.status || 'Unknown'}
          </Tag>
          <Text>Slot {slot} / {maxSlot}</Text>
        </Space>
      </div>

      <AmapScene frame={frame} center={center} />

      <Card className="control-card">
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <Space wrap>
            <Button type="primary" onClick={handlePlay} disabled={isPlaying}>
              Play
            </Button>
            <Button onClick={handlePause} disabled={!isPlaying}>
              Pause
            </Button>
            <Button danger onClick={handleStop}>
              Stop
            </Button>
            <Button onClick={() => setSlot(Math.max(slot - 1, 0))}>
              Prev
            </Button>
            <Button onClick={() => setSlot(Math.min(slot + 1, maxSlot))}>
              Next
            </Button>
          </Space>

          <Space wrap>
            <Text>Playback speed (ms)</Text>
            <InputNumber
              min={200}
              max={2000}
              step={100}
              value={intervalMs}
              onChange={value => setIntervalMs(Number(value || 800))}
            />
          </Space>

          <Slider
            min={0}
            max={maxSlot}
            value={slot}
            onChange={value => {
              if (Array.isArray(value)) return;
              setSlot(value);
            }}
          />

          <Space wrap>
            <Card size="small" className="metric-card">
              <Text type="secondary">Throughput</Text>
              <div className="metric-value">{frame?.metrics?.throughput?.toFixed(2) || '--'}</div>
            </Card>
            <Card size="small" className="metric-card">
              <Text type="secondary">Latency</Text>
              <div className="metric-value">{frame?.metrics?.latency?.toFixed(2) || '--'}</div>
            </Card>
          </Space>
        </Space>
      </Card>
    </div>
  );
}
