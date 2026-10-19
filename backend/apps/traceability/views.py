from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from apps.inventory.models import Batch
from .services import TraceabilityService

class ForwardTraceView(APIView):
    """API endpoint to trace forward from a raw material lot."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, batch_id):
        try:
            batch = Batch.objects.get(id=batch_id)
            data = TraceabilityService.trace_forward_from_raw_lot(batch)
            return Response(data)
        except Batch.DoesNotExist:
            return Response({'error': 'Batch not found'}, status=status.HTTP_404_NOT_FOUND)


class ReverseTraceView(APIView):
    """API endpoint to trace reverse from a finished formulated batch."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, batch_id):
        try:
            batch = Batch.objects.get(id=batch_id)
            data = TraceabilityService.trace_reverse_from_finished_batch(batch)
            return Response(data)
        except Batch.DoesNotExist:
            return Response({'error': 'Batch not found'}, status=status.HTTP_404_NOT_FOUND)


class RecallExposureView(APIView):
    """API endpoint to calculate urgent market and warehouse recall exposure."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, batch_id):
        try:
            batch = Batch.objects.get(id=batch_id)
            data = TraceabilityService.calculate_recall_exposure(batch)
            return Response(data)
        except Batch.DoesNotExist:
            return Response({'error': 'Batch not found'}, status=status.HTTP_404_NOT_FOUND)
