import api from "./client";

export const generateSeating = async (data) => {
  return api.post("seating/generate/", data);
};
