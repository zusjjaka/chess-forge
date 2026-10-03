import grpc

from grpc_gen.repertoire.v1 import repertoire_pb2_grpc
from rpc.service import RepertoireGrpcService


async def create_grpc_server() -> grpc.aio.Server:
    server = grpc.aio.server()

    repertoire_pb2_grpc.add_RepertoireServiceServicer_to_server(
        RepertoireGrpcService(),
        server,
    )

    server.add_insecure_port('[::]:50051')

    await server.start()

    return server
