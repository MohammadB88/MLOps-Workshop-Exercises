from kfp import dsl, compiler
from kfp.dsl import InputPath, OutputPath

IMAGE_DATA_SCIENCE = "quay.io/modh/runtime-images:runtime-datascience-ubi9-python-3.11-20250703"

@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "seaborn"]
    )
def create_dataset(dataset_path: OutputPath('Dataset'),):
    import json
    dataset = {'my_dataset': [[1, 2, 3], [4, 5, 6]]}
    with open(dataset_path, 'w') as f:
        json.dump(dataset, f)

    print('***************************************')
    print('Output of this step!')
    print('***************************************')
    print(dataset_path)


@dsl.component(
    base_image=IMAGE_DATA_SCIENCE,
    packages_to_install=["requests", "seaborn"]
    )
def consume_dataset(dataset: InputPath('Dataset')):
    print('***************************************')
    print('Output of this step!')
    print('***************************************')
    print(dataset)


@dsl.pipeline(name='my-pipeline', pipeline_root='s3://runpipelines')
def my_pipeline():
    create_dataset_op = create_dataset()
    consume_dataset(dataset=create_dataset_op.outputs['dataset_path'])


compiler.Compiler().compile(my_pipeline, "testpipeline.yaml")