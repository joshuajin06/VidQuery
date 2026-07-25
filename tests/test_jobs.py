from services.jobs import Job, JobStatus, create_job, get_job, update_job


def test_create_job_has_pending_status():
    job = create_job()
    assert job.status == JobStatus.PENDING


def test_create_job_generates_distinct_ids():
    job_a = create_job()
    job_b = create_job()
    assert job_a.id != job_b.id


def test_created_job_is_retrievable():
    job = create_job()
    assert get_job(job.id) is job


def test_get_job_returns_none_for_unknown_id():
    assert get_job("does-not-exist") is None


def test_update_job_mutates_the_stored_job():
    job = create_job()
    update_job(job.id, status=JobStatus.DONE, summary="finished")

    stored = get_job(job.id)
    assert stored.status == JobStatus.DONE
    assert stored.summary == "finished"


def test_update_job_only_touches_given_fields():
    job = create_job()
    update_job(job.id, status=JobStatus.SUMMARIZING)

    stored = get_job(job.id)
    assert stored.status == JobStatus.SUMMARIZING
    assert stored.summary is None  # untouched field keeps its default
