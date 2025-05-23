package service

import (
	"github.com/google/uuid"
	"github.com/raghavyuva/nixopus-api/internal/features/logger"
	"github.com/raghavyuva/nixopus-api/internal/features/organization/types"
	shared_types "github.com/raghavyuva/nixopus-api/internal/types"
)

// GetOrganizationUsers fetches the users for a given organization.
//
// It first checks if the organization exists by calling the storage layer's GetOrganization method.
// If the organization does not exist, it returns ErrOrganizationDoesNotExist.
// If the organization exists, it calls the storage layer's GetOrganizationUsers method to fetch the users.
// If the storage layer returns an error, it returns ErrFailedToGetOrganizationUsers.
// If the storage layer succeeds in fetching the users, it returns the users.
func (o *OrganizationService) GetOrganizationUsers(id string) ([]shared_types.OrganizationUsers, error) {
	o.logger.Log(logger.Info, "getting organization users", id)
	existingOrganization, err := o.storage.GetOrganization(id)
	if err != nil && existingOrganization.ID == uuid.Nil {
		o.logger.Log(logger.Error, types.ErrOrganizationDoesNotExist.Error(), "")
		return nil, types.ErrOrganizationDoesNotExist
	}

	users, err := o.storage.GetOrganizationUsers(id)

	if err != nil {
		o.logger.Log(logger.Error, types.ErrFailedToGetOrganizationUsers.Error(), err.Error())
		return nil, types.ErrFailedToGetOrganizationUsers
	}

	return users, nil
}
