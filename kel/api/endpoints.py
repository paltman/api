from pinax import api

from .authentication import KelIdentityAuthentication
from .permissions import (
    ensure_token_match,
    ensure_user_belongs
)
from .resources import ResourceGroupResource


class ResourceGroupSiteCollectionRelationship(api.RelationshipEndpointSet):

    middleware = {
        "authentication": [
            KelIdentityAuthentication(),
        ],
        "permissions": {
            ensure_user_belongs("resource_group"),
        },
    }

    def get_queryset(self):
        return self.request.user.resource_groups()

    def prepare(self):
        self.resource_group = self.get_object_or_404(
            self.get_queryset(),
            name=self.kwargs["resource_group"],
        )

    def retrieve(self, request, *args, **kwargs):
        qs = (
            self.request.user.sites()
            .filter(resource_group=self.resource_group)
            .order_by("resource_group__name", "name")
        )
        return self.render(api.registry["site"].from_queryset(qs))


@api.bind(resource=ResourceGroupResource)
class ScopedResourceGroupEndpointSet(api.ResourceEndpointSet):

    url = api.url(
        base_name="resource-group",
        base_regex=r"resource-groups",
        lookup={
            "field": "resource_group",
            "regex": r"[a-zA-Z0-9_-]+"
        }
    )
    middleware = {
        "authentication": [
            KelIdentityAuthentication(),
        ],
        "permissions": {
            ensure_token_match("abc", check_methods=["create"]),
            ensure_user_belongs("resource_group", check_methods=["retrieve", "update", "destroy"]),
        },
    }
    relationships = {
        "sites": ResourceGroupSiteCollectionRelationship,
    }

    def get_queryset(self):
        return self.request.user.resource_groups()

    def prepare(self):
        if self.requested_method in ["retrieve", "update", "destroy"]:
            self.resource_group = self.get_object_or_404(
                self.get_queryset(),
                name=self.kwargs["resource_group"],
            )

    def list(self, request, *args, **kwargs):
        return self.render(self.resource_class.from_queryset(self.get_queryset()))

    def create(self, request, *args, **kwargs):
        with self.validate(self.resource_class) as resource:
            resource.save(
                create_kwargs={
                    "owner": request.user,
                }
            )
        return self.render_create(resource)

    def retrieve(self, request, *args, **kwargs):
        resource = self.resource_class(self.resource_group)
        return self.render(resource)

    def update(self, request, *args, **kwargs):
        with self.validate(self.resource_class, obj=self.resource_group) as resource:
            resource.save()
        return self.render(resource)

    def destroy(self, request, *args, **kwargs):
        self.resource_group.delete()
        return self.render_delete()
