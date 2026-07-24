from app.models.duplicati_job import (
    DuplicatiJob,
)


def test_duplicati_job_creation():

    job = DuplicatiJob(
        name="test-backup",
        source_paths=[
            "/data/test"
        ],
        destination_url=(
            "file:///backup"
        ),
    )

    assert job.name == "test-backup"

    assert job.source_paths == [
        "/data/test"
    ]

    assert job.destination_url == (
        "file:///backup"
    )


def test_duplicati_job_to_payload():

    job = DuplicatiJob(
        name="test-backup",
        source_paths=[
            "/data/test"
        ],
        destination_url=(
            "file:///backup"
        ),
        description="Backup test",
        encryption="AES-256",
        compression="zip",
        retention_policy="7D",
        options={
            "test": True,
        },
        metadata={
            "origin": "CasaOS",
        },
    )


    payload = job.to_payload()


    assert payload["name"] == (
        "test-backup"
    )

    assert payload["source_paths"] == [
        "/data/test"
    ]

    assert payload["destination_url"] == (
        "file:///backup"
    )

    assert payload["encryption"] == (
        "AES-256"
    )

    assert payload["compression"] == (
        "zip"
    )

    assert payload["retention_policy"] == (
        "7D"
    )

    assert payload["options"] == {
        "test": True,
    }

    assert payload["metadata"] == {
        "origin": "CasaOS",
    }


def test_duplicati_job_to_payload_does_not_modify_model():

    options = {
        "keep": True,
    }

    metadata = {
        "source": "test",
    }


    job = DuplicatiJob(
        name="backup",
        source_paths=[
            "/source"
        ],
        destination_url=(
            "file:///dest"
        ),
        options=options,
        metadata=metadata,
    )


    payload = job.to_payload()


    payload["options"]["keep"] = False

    payload["metadata"]["source"] = (
        "changed"
    )


    assert job.options == {
        "keep": True,
    }

    assert job.metadata == {
        "source": "test",
    }