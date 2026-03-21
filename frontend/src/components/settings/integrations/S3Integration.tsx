'use client';

import { useCallback, useState } from 'react';
import Button from '@/components/ui/Button';
import { useToast } from '@/components/ui/Toast';
import api from '@/lib/api';
import type { S3Config, StorageProvider, TestResult } from './types';

const PROVIDER_OPTIONS: { value: StorageProvider; label: string }[] = [
  { value: 'aws', label: 'Amazon S3 (AWS)' },
  { value: 'gcs', label: 'Google Cloud Storage' },
  { value: 'azure', label: 'Azure Blob Storage' },
];

interface S3IntegrationProps {
  initial?: Partial<S3Config>;
  onSave: (config: S3Config) => void;
  onBack: () => void;
}

export default function S3Integration({ initial, onSave, onBack }: S3IntegrationProps) {
  const { addToast } = useToast();
  const [provider, setProvider] = useState<StorageProvider>(initial?.provider ?? 'aws');
  const [bucket, setBucket] = useState(initial?.bucket ?? '');
  const [region, setRegion] = useState(initial?.region ?? '');
  const [accessKey, setAccessKey] = useState(initial?.accessKey ?? '');
  const [secretKey, setSecretKey] = useState(initial?.secretKey ?? '');
  const [testing, setTesting] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleTest = useCallback(async () => {
    if (!bucket || !accessKey || !secretKey) {
      addToast('warning', 'Please fill in bucket, access key, and secret key.');
      return;
    }
    setTesting(true);
    try {
      const { data } = await api.post<TestResult>('/api/integrations/s3/test', {
        provider,
        bucket,
        region,
        access_key: accessKey,
        secret_key: '***', // never send real secret in test preview
      });
      addToast(data.ok ? 'success' : 'error', data.message);
    } catch {
      addToast('error', 'Failed to test storage connection.');
    } finally {
      setTesting(false);
    }
  }, [provider, bucket, region, accessKey, secretKey, addToast]);

  const handleSave = useCallback(async () => {
    if (!bucket) {
      addToast('warning', 'Bucket name is required.');
      return;
    }
    setSaving(true);
    try {
      await api.post('/api/integrations', {
        type: 's3',
        config: {
          provider,
          bucket,
          region,
          access_key: accessKey,
          secret_key: secretKey,
        },
      });
      onSave({ provider, bucket, region, accessKey, secretKey });
      addToast('success', 'Storage integration saved.');
    } catch {
      addToast('error', 'Failed to save storage integration.');
    } finally {
      setSaving(false);
    }
  }, [provider, bucket, region, accessKey, secretKey, onSave, addToast]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          aria-label="Back"
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <h3 className="text-lg font-semibold text-gray-900">Object Storage Integration</h3>
      </div>

      {/* Provider */}
      <div>
        <label htmlFor="s3-provider" className="block text-sm font-medium text-gray-700 mb-1">
          Provider
        </label>
        <select
          id="s3-provider"
          value={provider}
          onChange={(e) => setProvider(e.target.value as StorageProvider)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500 bg-white"
        >
          {PROVIDER_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Bucket */}
      <div>
        <label htmlFor="s3-bucket" className="block text-sm font-medium text-gray-700 mb-1">
          Bucket Name
        </label>
        <input
          id="s3-bucket"
          type="text"
          value={bucket}
          onChange={(e) => setBucket(e.target.value)}
          placeholder="my-bucket"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Region */}
      <div>
        <label htmlFor="s3-region" className="block text-sm font-medium text-gray-700 mb-1">
          Region
        </label>
        <input
          id="s3-region"
          type="text"
          value={region}
          onChange={(e) => setRegion(e.target.value)}
          placeholder="us-east-1"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Access Key */}
      <div>
        <label htmlFor="s3-access-key" className="block text-sm font-medium text-gray-700 mb-1">
          Access Key
        </label>
        <input
          id="s3-access-key"
          type="text"
          value={accessKey}
          onChange={(e) => setAccessKey(e.target.value)}
          placeholder="AKIA..."
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Secret Key (masked) */}
      <div>
        <label htmlFor="s3-secret-key" className="block text-sm font-medium text-gray-700 mb-1">
          Secret Key
        </label>
        <input
          id="s3-secret-key"
          type="password"
          value={secretKey}
          onChange={(e) => setSecretKey(e.target.value)}
          placeholder="Enter secret key"
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
        />
      </div>

      {/* Actions */}
      <div className="flex items-center gap-3 pt-2">
        <Button variant="secondary" onClick={handleTest} loading={testing}>
          Test Connection
        </Button>
        <Button onClick={handleSave} loading={saving}>
          Save
        </Button>
      </div>
    </div>
  );
}
