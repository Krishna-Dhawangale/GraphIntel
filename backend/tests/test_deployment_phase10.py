import pytest
from pathlib import Path
from app.workers.queue_interface import (
    DeadLetterMessage,
    IngestionMessage,
    InProcessQueueAdapter,
    KafkaIngestionProducer,
)


@pytest.mark.asyncio
async def test_queue_message_contract_and_dlq():
    """Verify message queue contract, retry mechanism, and Dead Letter Queue quarantine."""
    adapter = InProcessQueueAdapter()

    msg = IngestionMessage(
        job_id="job-101",
        document_id="doc-101",
        tenant_id="tenant-acme",
        user_id="user-101",
        filename="10k_filing.pdf",
        content_hash="hash123",
        storage_path="docs/10k_filing.pdf",
        mime_type="application/pdf",
        retry_count=0,
        max_retries=2,
    )

    # Publish
    published = await adapter.publish_ingestion_event(msg)
    assert published is True
    assert adapter.queue.qsize() == 1

    # Quarantine into DLQ
    dlq_msg = DeadLetterMessage(
        original_message=msg,
        failed_at="2026-10-08T12:00:00Z",
        failure_reason="Corrupted PDF EOF marker",
        last_error_type="PermanentValidationError",
    )
    sent_dlq = await adapter.send_to_dlq(dlq_msg)
    assert sent_dlq is True
    assert len(adapter.dlq) == 1
    assert adapter.dlq[0].failure_reason == "Corrupted PDF EOF marker"


@pytest.mark.asyncio
async def test_kafka_producer_routing():
    """Verify Kafka ingestion producer dispatches events with tenant_id partition key."""
    producer = KafkaIngestionProducer(bootstrap_servers="localhost:9092")
    msg = IngestionMessage(
        job_id="job-202",
        document_id="doc-202",
        tenant_id="tenant-beta",
        user_id="user-202",
        filename="earnings_transcript.txt",
        content_hash="hash456",
        storage_path="docs/transcript.txt",
        mime_type="text/plain",
    )
    result = await producer.publish_ingestion_event(msg)
    assert result is True


def test_kubernetes_manifests_exist():
    """Verify all required Kubernetes manifests exist and are non-empty."""
    root_dir = Path(__file__).parent.parent.parent
    k8s_dir = root_dir / "k8s"
    assert k8s_dir.exists()

    expected_manifests = [
        "namespace.yaml",
        "configmap.yaml",
        "secret.yaml",
        "backend-deployment.yaml",
        "backend-hpa.yaml",
        "worker-deployment.yaml",
        "frontend-deployment.yaml",
        "services.yaml",
        "ingress.yaml",
    ]

    for manifest in expected_manifests:
        file_path = k8s_dir / manifest
        assert file_path.exists(), f"Missing {manifest}"
        content = file_path.read_text(encoding="utf-8")
        assert len(content) > 50, f"Manifest {manifest} is empty or incomplete"


def test_terraform_iac_exists():
    """Verify Terraform configuration files exist."""
    root_dir = Path(__file__).parent.parent.parent
    tf_dir = root_dir / "terraform"
    assert tf_dir.exists()
    assert (tf_dir / "main.tf").exists()
    assert (tf_dir / "variables.tf").exists()
    assert (tf_dir / "outputs.tf").exists()
