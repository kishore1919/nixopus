package controller

import (
	"net/http"

	"github.com/go-fuego/fuego"
	"github.com/raghavyuva/nixopus-api/internal/features/logger"
	"github.com/raghavyuva/nixopus-api/internal/features/user/types"
	"github.com/raghavyuva/nixopus-api/internal/utils"

	shared_types "github.com/raghavyuva/nixopus-api/internal/types"
)

func (u *UserController) UpdateAvatar(s fuego.ContextWithBody[types.UpdateAvatarRequest]) (*shared_types.Response, error) {
	u.logger.Log(logger.Info, "updating user avatar", "")

	req, err := s.Body()
	if err != nil {
		return nil, fuego.HTTPError{
			Err:    err,
			Status: http.StatusBadRequest,
		}
	}

	w, r := s.Response(), s.Request()

	if !u.parseAndValidate(w, r, &req) {
		return nil, fuego.HTTPError{
			Err:    nil,
			Status: http.StatusBadRequest,
		}
	}

	user := utils.GetUser(w, r)
	if user == nil {
		return nil, fuego.HTTPError{
			Err:    nil,
			Status: http.StatusUnauthorized,
		}
	}

	err = u.service.UpdateAvatar(s.Request().Context(), user.ID.String(), &req)
	if err != nil {
		u.logger.Log(logger.Error, err.Error(), "")
		return nil, fuego.HTTPError{
			Err:    err,
			Status: http.StatusInternalServerError,
		}
	}

	u.cache.InvalidateUser(u.ctx, user.ID.String())

	return &shared_types.Response{
		Status:  "success",
		Message: "Avatar updated successfully",
	}, nil
}
