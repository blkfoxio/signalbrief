"""Company views."""

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

from .models import Company
from .serializers import CompanySerializer


@api_view(["GET"])
def company_list(request):
    """List companies analyzed by the current user."""
    companies = Company.objects.filter(created_by=request.user).select_related("enrichment")
    serializer = CompanySerializer(companies, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def company_detail(request, domain):
    """Get company detail by domain."""
    try:
        company = Company.objects.select_related("enrichment").get(domain=domain)
    except Company.DoesNotExist:
        return Response({"error": "Company not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(CompanySerializer(company).data)
