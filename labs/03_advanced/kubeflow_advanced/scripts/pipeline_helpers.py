"""Helper functions for KFP pipeline creation, compilation, and scheduling."""

import kfp
from kfp import dsl, Client
from kfp.dsl import component
from typing import Callable, Optional, Any
import logging

logger = logging.getLogger(__name__)


def create_pipeline_component(
    func: Callable,
    base_image: str = "python:3.11",
    packages_to_install: Optional[list[str]] = None,
    cpu_request: str = "500m",
    memory_request: str = "1Gi",
    cpu_limit: Optional[str] = None,
    memory_limit: Optional[str] = None,
    accelerator_type: Optional[str] = None,
    accelerator_limit: Optional[int] = None,
) -> Any:
    """Wrap a Python function as a KFP component with resource configuration.

    Args:
        func: The Python function to convert into a pipeline component.
        base_image: Container image for the component.
        packages_to_install: List of PyPI packages to install.
        cpu_request: Minimum CPU resources (e.g., "500m", "2").
        memory_request: Minimum memory resources (e.g., "1Gi", "4Gi").
        cpu_limit: Maximum CPU resources. Defaults to cpu_request if None.
        memory_limit: Maximum memory resources. Defaults to memory_request if None.
        accelerator_type: GPU accelerator type (e.g., "nvidia.com/gpu").
        accelerator_limit: Number of accelerators to request.

    Returns:
        A KFP component decorated function with resource specifications.
    """
    comp = component(
        func=func,
        base_image=base_image,
        packages_to_install=packages_to_install or [],
    )

    class ResourceComponent:
        """Wrapper that applies resource config when called in a pipeline."""

        def __init__(self, component_func, resource_kwargs):
            self._component_func = component_func
            self._resource_kwargs = resource_kwargs

        def __call__(self, *args, **kwargs):
            task = self._component_func(*args, **kwargs)
            task.set_cpu_request(self._resource_kwargs.get("cpu_request", "500m"))
            task.set_memory_request(self._resource_kwargs.get("memory_request", "1Gi"))
            if self._resource_kwargs.get("cpu_limit"):
                task.set_cpu_limit(self._resource_kwargs["cpu_limit"])
            if self._resource_kwargs.get("memory_limit"):
                task.set_memory_limit(self._resource_kwargs["memory_limit"])
            if self._resource_kwargs.get("accelerator_type"):
                task.set_accelerator_type(self._resource_kwargs["accelerator_type"])
                if self._resource_kwargs.get("accelerator_limit"):
                    task.set_accelerator_limit(self._resource_kwargs["accelerator_limit"])
            return task

    resource_kwargs = {
        "cpu_request": cpu_request,
        "memory_request": memory_request,
        "cpu_limit": cpu_limit or cpu_request,
        "memory_limit": memory_limit or memory_request,
        "accelerator_type": accelerator_type,
        "accelerator_limit": accelerator_limit,
    }

    return ResourceComponent(comp, resource_kwargs)


def generate_pipeline_yaml(
    pipeline_func: Callable,
    output_path: str = "pipeline.yaml",
) -> str:
    """Compile a KFP pipeline function to a YAML file.

    Args:
        pipeline_func: The decorated pipeline function (with @dsl.pipeline).
        output_path: File path for the generated YAML.

    Returns:
        The path to the generated YAML file.
    """
    try:
        kfp.compiler.Compiler().compile(
            pipeline_func=pipeline_func,
            package_path=output_path,
        )
        logger.info(f"Pipeline compiled to {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Failed to compile pipeline: {e}")
        raise


def schedule_pipeline(
    client: Client,
    experiment_name: str,
    pipeline_func: Callable,
    cron_expression: str = "0 0 * * *",
    enable_caching: bool = True,
    parameters: Optional[dict[str, Any]] = None,
    job_name: Optional[str] = None,
) -> str:
    """Schedule a KFP pipeline as a recurring run.

    Args:
        client: Authenticated KFP client instance.
        experiment_name: Name of the experiment to create/use.
        pipeline_func: The decorated pipeline function.
        cron_expression: Standard cron expression for scheduling.
        enable_caching: Whether to enable KFP caching for the pipeline.
        parameters: Dictionary of pipeline parameters.
        job_name: Name for the recurring run job.

    Returns:
        The job ID of the created recurring run.
    """
    try:
        experiment = client.create_experiment(
            name=experiment_name,
            description=f"Recurring runs for {experiment_name}",
        )
        logger.info(f"Experiment '{experiment_name}' ready")
    except Exception as e:
        logger.warning(f"Could not create experiment (may already exist): {e}")

    pipeline_yaml = generate_pipeline_yaml(pipeline_func)

    job_name = job_name or f"{experiment_name}-job"

    try:
        run = client.create_recurring_run(
            experiment_name=experiment_name,
            job_name=job_name,
            cron_schedule=cron_expression,
            pipeline_package_path=pipeline_yaml,
            params=parameters or {},
            enable_caching=enable_caching,
        )
        logger.info(f"Recurring run created: {run}")
        return run
    except AttributeError:
        logger.warning(
            "create_recurring_run API not available in this KFP version. "
            "Falling back to run_pipeline."
        )
        run = client.run_pipeline(
            experiment_id=experiment.id,
            job_name=job_name,
            pipeline_package_path=pipeline_yaml,
            params=parameters or {},
        )
        logger.info(f"One-time pipeline run created: {run}")
        return run
    except Exception as e:
        logger.error(f"Failed to schedule pipeline: {e}")
        raise
